"""Read mission POIs from the MSL spreadsheet and landing sites from config."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from location_service.domain.geo import validate_lat_lon
from location_service.domain.models import Coordinate, Place
from location_service.domain.text import normalize_text
from location_service.ingest.config_loader import MissionConfig

# columns that map to dedicated Place fields, everything else -> properties
_FIELD_COLUMNS = {"nombre", "lon", "lat", "elevacion_m"}
_REQUIRED_COLUMNS = {"nombre", "sol", "lon", "lat", "elevacion_m"}


class IngestError(Exception):
    """Fatal ingestion problem (bad file, undetectable convention, ...)."""


def slugify(name: str) -> str:
    return "-".join(normalize_text(name).split())


def _discard(report: dict[str, Any], record: str, reason: str) -> None:
    report.setdefault("discarded", []).append(
        {"source": "mission_msl", "record": record, "reason": reason}
    )


def _unique_id(base: str, seen: set[str], report: dict[str, Any], source: str) -> str:
    candidate, n = base, 2
    while candidate in seen:
        candidate = f"{base}-{n}"
        n += 1
    if candidate != base:
        report.setdefault("id_collisions", []).append(
            {"source": source, "base_id": base, "id": candidate}
        )
    seen.add(candidate)
    return candidate


def read_mission_points(
    xlsx_path: Path,
    config: MissionConfig,
    report: dict[str, Any],
    seen_ids: set[str],
) -> list[Place]:
    """Read the MSL targets spreadsheet (layer B) into Place objects."""
    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        raise IngestError(f"mission file not found: {xlsx_path}")

    excel = pd.ExcelFile(xlsx_path)
    sheet = (
        "Objetivos_Minerales"
        if "Objetivos_Minerales" in excel.sheet_names
        else excel.sheet_names[0]
    )
    if sheet != "Objetivos_Minerales":
        report.setdefault("warnings", []).append(
            f"sheet 'Objetivos_Minerales' not found; using '{sheet}'"
        )
    df = pd.read_excel(excel, sheet_name=sheet)

    missing = _REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise IngestError(f"mission file missing required columns: {sorted(missing)}")

    places: list[Place] = []
    name_to_tags: dict[str, list[str]] = {}
    for tag, names in config.tags.items():
        for n in names:
            name_to_tags.setdefault(n, []).append(tag)

    for _, row in df.iterrows():
        nombre = row.get("nombre")
        record = str(nombre) if nombre is not None else f"row_{_}"
        if (
            nombre is None
            or (isinstance(nombre, float) and math.isnan(nombre))
            or not str(nombre).strip()
        ):
            _discard(report, record, "missing nombre")
            continue
        nombre = str(nombre).strip()
        try:
            lat, lon = validate_lat_lon(float(row["lat"]), float(row["lon"]))
        except (TypeError, ValueError) as exc:
            _discard(report, nombre, f"invalid coordinates: {exc}")
            continue

        properties: dict[str, Any] = {}
        for col in df.columns:
            if col in _FIELD_COLUMNS:
                continue
            value = row[col]
            if value is None:
                continue
            try:
                if isinstance(value, float) and math.isnan(value):
                    continue
            except TypeError:
                pass
            if hasattr(value, "item"):
                value = value.item()
            properties[str(col)] = value

        slug = slugify(nombre)
        pid = _unique_id(f"mars:msl:{slug}", seen_ids, report, "mission_msl")
        places.append(
            Place(
                id=pid,
                name=nombre,
                body="mars",
                kind="poi",
                feature_type="mission_target",
                source="mission_msl",
                center=Coordinate(lat=lat, lon=lon),
                name_norm=normalize_text(nombre),
                elevation_m=(
                    None
                    if pd.isna(row["elevacion_m"])
                    else float(row["elevacion_m"])
                ),
                tags=tuple(name_to_tags.get(nombre, ())),
                properties=properties,
            )
        )

    for site in config.landing_sites:
        name = str(site["name"])
        slug = str(site.get("slug") or slugify(name))
        lat, lon = validate_lat_lon(float(site["lat"]), float(site["lon"]))
        properties = {"note": str(site["note"])} if site.get("note") else {}
        pid = _unique_id(f"mars:msl:{slug}", seen_ids, report, "mission_msl")
        places.append(
            Place(
                id=pid,
                name=name,
                body="mars",
                kind="landing_site",
                feature_type="landing_site",
                source="mission_msl",
                center=Coordinate(lat=lat, lon=lon),
                name_norm=normalize_text(name),
                properties=properties,
            )
        )
    return places
