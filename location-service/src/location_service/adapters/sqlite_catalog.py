"""Read-only SQLite catalog loader (adapter).

The catalog is built offline by `location_service.ingest`; at runtime it is
opened read-only (mode=ro) and fully loaded into memory.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from location_service.domain.models import Bbox, Coordinate, Place, Region


class CatalogNotFoundError(FileNotFoundError):
    pass


@dataclass(frozen=True)
class CatalogData:
    places: tuple[Place, ...]
    regions: tuple[Region, ...]
    meta: dict[str, str]


def _opt_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _place_from_row(row: sqlite3.Row, aliases: list[str]) -> Place:
    bbox = None
    if row["bbox_west"] is not None:
        bbox = Bbox(
            west=float(row["bbox_west"]),
            south=float(row["bbox_south"]),
            east=float(row["bbox_east"]),
            north=float(row["bbox_north"]),
        )
    return Place(
        id=row["id"],
        name=row["name"],
        body=row["body"],
        kind=row["kind"],
        feature_type=row["feature_type"],
        source=row["source"],
        center=Coordinate(lat=float(row["lat"]), lon=float(row["lon"])),
        name_clean=row["name_clean"],
        name_norm=row["name_norm"],
        bbox=bbox,
        diameter_km=_opt_float(row["diameter_km"]),
        elevation_m=_opt_float(row["elevation_m"]),
        approval_status=row["approval_status"],
        origin=row["origin"],
        tags=tuple(json.loads(row["tags_json"])),
        aliases=tuple(aliases),
        properties=json.loads(row["properties_json"]),
    )


def load_catalog(path: Path) -> CatalogData:
    """Load the whole catalog from SQLite (read-only)."""
    path = Path(path)
    if not path.exists():
        raise CatalogNotFoundError(str(path))
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        aliases_by_place: dict[str, list[str]] = {}
        for a in conn.execute("SELECT place_id, alias FROM aliases ORDER BY alias"):
            aliases_by_place.setdefault(a["place_id"], []).append(a["alias"])

        places = tuple(
            _place_from_row(r, aliases_by_place.get(r["id"], []))
            for r in conn.execute("SELECT * FROM places ORDER BY id")
        )
        regions = tuple(
            Region(
                id=r["id"],
                name=r["name"],
                kind=r["kind"],
                source=r["source"],
                bbox=(
                    Bbox(
                        west=float(r["bbox_west"]),
                        south=float(r["bbox_south"]),
                        east=float(r["bbox_east"]),
                        north=float(r["bbox_north"]),
                    )
                    if r["bbox_west"] is not None
                    else None
                ),
                note=r["note"],
            )
            for r in conn.execute("SELECT * FROM regions ORDER BY id")
        )
        meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM catalog_meta")}
    finally:
        conn.close()
    return CatalogData(places=places, regions=regions, meta=meta)
