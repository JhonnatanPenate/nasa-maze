"""Read the USGS Gazetteer of Planetary Nomenclature (layer A).

Format is detected by extension (.csv, .tsv, .geojson, .shp). Column names are
NEVER assumed: config.gazetteer.columns maps canonical fields to real names.
Longitude convention is detected or taken from config.convention.lon.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, cast

import pandas as pd

from location_service.domain.geo import normalize_lon, validate_lat_lon
from location_service.domain.models import Bbox, Coordinate, Place
from location_service.domain.text import normalize_text
from location_service.ingest.config_loader import GazetteerConfig
from location_service.ingest.mission_points import IngestError, _unique_id, slugify

_LON_CONVENTIONS = {"auto", "east_0_360", "signed_180_180", "west_positive"}


def _f(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _s(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    return text or None


def detect_lon_convention(values: list[float], declared: str) -> str:
    """Resolve the longitude convention of a Gazetteer column.

    Raises IngestError when it cannot be detected (spec 3.5 step 3).
    """
    if declared != "auto":
        if declared not in _LON_CONVENTIONS:
            raise IngestError(f"unknown convention.lon: {declared!r}")
        return declared
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        raise IngestError("no longitude values available to detect convention")
    has_neg = any(v < 0 for v in vals)
    has_gt180 = any(v > 180 for v in vals)
    if has_neg and has_gt180:
        raise IngestError(
            "longitude column mixes negative and >180 values; cannot detect "
            "convention - set convention.lon explicitly in gazetteer_columns.yaml"
        )
    if has_neg:
        return "signed_180_180"
    if has_gt180:
        return "east_0_360"
    raise IngestError(
        "all longitudes lie within [0, 180]; cannot distinguish east 0-360 "
        "from west-positive - set convention.lon explicitly"
    )


def to_east_lon(value: float, convention: str) -> float:
    """Convert a source longitude to east-positive degrees (any range)."""
    if convention == "west_positive":
        return (360.0 - value) % 360.0
    return value % 360.0  # east_0_360 and signed_180_180 both normalize via %360


def _discard(report: dict[str, Any], record: str, reason: str) -> None:
    report.setdefault("discarded", []).append(
        {"source": "iau_gazetteer", "record": record, "reason": reason}
    )


def _read_tabular(path: Path) -> list[dict[str, Any]]:
    sep = "	" if path.suffix.lower() == ".tsv" else ","
    df = pd.read_csv(path, sep=sep)
    return cast(list[dict[str, Any]], df.to_dict(orient="records"))


def _geometry_lat_lon(geometry: dict[str, Any]) -> tuple[float, float] | None:
    """Derive (lat, lon) from GeoJSON geometry: Point coords or bbox center."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point" and isinstance(coords, list) and len(coords) >= 2:
        return float(coords[1]), float(coords[0])
    # collect all positions for a bbox-center estimate
    positions: list[list[float]] = []

    def walk(c: Any) -> None:
        if isinstance(c, list) and len(c) >= 2 and isinstance(c[0], (int, float)):
            positions.append(c)
        elif isinstance(c, list):
            for item in c:
                walk(item)

    if coords is not None:
        walk(coords)
    if not positions:
        return None
    lons = [p[0] for p in positions]
    lats = [p[1] for p in positions]
    return (min(lats) + max(lats)) / 2.0, (min(lons) + max(lons)) / 2.0


def _read_geojson(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    rows: list[dict[str, Any]] = []
    for feature in data.get("features", []):
        row = dict(feature.get("properties") or {})
        geom = feature.get("geometry")
        if geom:
            derived = _geometry_lat_lon(geom)
            if derived is not None:
                row.setdefault("__lat__", derived[0])
                row.setdefault("__lon__", derived[1])
        rows.append(row)
    return rows


def _read_shapefile(path: Path) -> list[dict[str, Any]]:
    try:
        import shapefile  # type: ignore[import-not-found]  # pyshp, optional ingest dep
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise IngestError(
            "shapefile input requires pyshp: pip install 'location-service[ingest]'"
        ) from exc
    rows: list[dict[str, Any]] = []
    with shapefile.Reader(str(path)) as reader:
        fields = [f[0] for f in reader.fields[1:]]
        for sr in reader.iterShapeRecords():
            shape, record = sr.shape, sr.record
            row = dict(zip(fields, record, strict=False))
            if shape.shapeType == shapefile.POINT:
                if shape.points:
                    row.setdefault("__lon__", shape.points[0][0])
                    row.setdefault("__lat__", shape.points[0][1])
            elif shape.bbox:
                west, south, east, north = shape.bbox
                row.setdefault("__lon__", (west + east) / 2.0)
                row.setdefault("__lat__", (south + north) / 2.0)
            rows.append(row)
    return rows


def _read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return _read_tabular(path)
    if suffix == ".geojson":
        return _read_geojson(path)
    if suffix == ".shp":
        return _read_shapefile(path)
    raise IngestError(f"unsupported gazetteer format: {path.suffix} (use .csv/.tsv/.geojson/.shp)")


def _col(config: GazetteerConfig, field: str) -> str | None:
    name = config.columns.get(field) or None
    return name if name else None


def _pick(row: dict[str, Any], column: str | None) -> Any:
    if column is None:
        return None
    return row.get(column)


def read_gazetteer(
    path: Path,
    config: GazetteerConfig,
    report: dict[str, Any],
    seen_ids: set[str],
) -> tuple[list[Place], str | None]:
    """Read a Gazetteer file into Place objects.

    Returns (places, detected_lon_convention).
    """
    path = Path(path)
    if not path.exists():
        raise IngestError(f"gazetteer file not found: {path}")
    rows = _read_rows(path)
    if not rows:
        raise IngestError(f"gazetteer file has no records: {path}")

    lat_col = _col(config, "lat")
    lon_col = _col(config, "lon")
    lon_west_col = _col(config, "lon_west")
    name_col = _col(config, "name")
    if name_col is None:
        # geojson/shapefile geometry fallback for coordinates
        if "__lat__" in rows[0]:
            lat_col = "__lat__"
        if "__lon__" in rows[0]:
            lon_col = "__lon__"
    if lat_col is None or (lon_col is None and lon_west_col is None):
        raise IngestError(
            "gazetteer_columns.yaml must map 'name' and 'lat' plus 'lon' or 'lon_west'"
        )

    if config.convention_lat == "planetographic":
        raise IngestError(
            "planetographic latitude is not supported in the MVP (section 3.2)"
        )
    if config.convention_lat != "planetocentric":
        raise IngestError(f"unknown convention.lat: {config.convention_lat!r}")

    # --- detect longitude convention on the `lon` column (rows not using lon_west)
    lon_values: list[float] = []
    for row in rows:
        if lon_west_col is not None and _s(_pick(row, lon_west_col)) is not None:
            continue
        v = _f(_pick(row, lon_col))
        if v is not None:
            lon_values.append(v)
    lon_convention = detect_lon_convention(lon_values, config.convention_lon)

    approval_col = _col(config, "approval_status")
    body_col = _col(config, "body")
    want_approved = config.approval_filter == "approved"

    places: list[Place] = []
    for index, row in enumerate(rows):
        record = _s(_pick(row, name_col)) or f"row_{index}"

        if body_col is not None:
            body_val = (_s(_pick(row, body_col)) or "").lower()
            if body_val and body_val != "mars":
                _discard(report, record, f"body is {body_val}, not mars")
                continue

        if want_approved:
            if approval_col is None:
                raise IngestError(
                    "approval filter is 'approved' but no approval_status column is mapped"
                )
            status = (_s(_pick(row, approval_col)) or "").lower()
            if status != "approved":
                _discard(report, record, f"approval_status is '{status or 'empty'}', not approved")
                continue

        name = _s(_pick(row, name_col))
        if name is None:
            _discard(report, record, "missing name")
            continue

        lat_raw = _f(_pick(row, lat_col))
        lon_raw = _f(_pick(row, lon_west_col)) if lon_west_col is not None else None
        lon_source = "west_positive"
        if lon_raw is None and lon_col is not None:
            lon_raw = _f(_pick(row, lon_col))
            lon_source = lon_convention
        if lat_raw is None or lon_raw is None:
            _discard(report, name, "missing coordinates")
            continue
        try:
            lat, lon_east = validate_lat_lon(lat_raw, to_east_lon(lon_raw, lon_source))
        except ValueError as exc:
            _discard(report, name, f"invalid coordinates: {exc}")
            continue

        feature_type = _s(_pick(row, _col(config, "feature_type"))) or "feature"
        explicit_id = _s(_pick(row, _col(config, "id")))
        base_id = (
            f"mars:iau:{explicit_id}"
            if explicit_id
            else f"mars:iau:{slugify(name)}-{slugify(feature_type)}"
        )
        pid = _unique_id(base_id, seen_ids, report, "iau_gazetteer")

        bbox = None
        bw = _f(_pick(row, _col(config, "bbox_west")))
        bs = _f(_pick(row, _col(config, "bbox_south")))
        be = _f(_pick(row, _col(config, "bbox_east")))
        bn = _f(_pick(row, _col(config, "bbox_north")))
        if None not in (bw, bs, be, bn):
            bbox = Bbox(west=bw, south=bs, east=be, north=bn)  # type: ignore[arg-type]

        name_clean = _s(_pick(row, _col(config, "name_clean")))
        places.append(
            Place(
                id=pid,
                name=name,
                body="mars",
                kind="feature",
                feature_type=feature_type,
                source="iau_gazetteer",
                center=Coordinate(lat=lat, lon=normalize_lon(lon_east)),
                name_clean=name_clean,
                name_norm=normalize_text(name_clean or name),
                bbox=bbox,
                diameter_km=_f(_pick(row, _col(config, "diameter_km"))),
                approval_status=_s(_pick(row, approval_col)) if approval_col else None,
                origin=_s(_pick(row, _col(config, "origin"))),
            )
        )
    return places, lon_convention
