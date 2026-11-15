"""Write the catalog SQLite file atomically (README 3.5 step 6)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from location_service.domain.models import Place, Region

SCHEMA_SQL = """
CREATE TABLE places (
    id TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    name TEXT NOT NULL,
    name_clean TEXT,
    name_norm TEXT NOT NULL,
    kind TEXT NOT NULL,
    feature_type TEXT NOT NULL,
    source TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    bbox_west REAL,
    bbox_south REAL,
    bbox_east REAL,
    bbox_north REAL,
    diameter_km REAL,
    elevation_m REAL,
    approval_status TEXT,
    origin TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    properties_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_places_name_norm ON places(name_norm);
CREATE INDEX idx_places_kind ON places(kind);
CREATE INDEX idx_places_source ON places(source);
CREATE INDEX idx_places_feature_type ON places(feature_type);

CREATE TABLE aliases (
    place_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_norm TEXT NOT NULL
);
CREATE INDEX idx_aliases_place ON aliases(place_id);
CREATE INDEX idx_aliases_norm ON aliases(alias_norm);

CREATE TABLE regions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    bbox_west REAL,
    bbox_south REAL,
    bbox_east REAL,
    bbox_north REAL,
    source TEXT NOT NULL,
    note TEXT
);

CREATE TABLE catalog_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_PLACE_COLUMNS = (
    "id", "body", "name", "name_clean", "name_norm", "kind", "feature_type",
    "source", "lat", "lon", "bbox_west", "bbox_south", "bbox_east", "bbox_north",
    "diameter_km", "elevation_m", "approval_status", "origin", "tags_json",
    "properties_json",
)


def place_to_row(place: Place) -> tuple[Any, ...]:
    bbox = place.bbox
    return (
        place.id,
        place.body,
        place.name,
        place.name_clean,
        place.name_norm,
        place.kind,
        place.feature_type,
        place.source,
        place.center.lat,
        place.center.lon,
        bbox.west if bbox else None,
        bbox.south if bbox else None,
        bbox.east if bbox else None,
        bbox.north if bbox else None,
        place.diameter_km,
        place.elevation_m,
        place.approval_status,
        place.origin,
        json.dumps(list(place.tags), sort_keys=True),
        json.dumps(place.properties, sort_keys=True, default=str),
    )


def write_catalog(
    path: Path,
    places: list[Place],
    aliases: dict[str, tuple[str, ...]],
    regions: tuple[Region, ...] | list[Region],
    meta: dict[str, str],
) -> None:
    """Write the catalog to a temp file, then rename atomically."""
    from location_service.domain.text import normalize_text

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        tmp.unlink()

    conn = sqlite3.connect(tmp)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            f"INSERT INTO places ({', '.join(_PLACE_COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(_PLACE_COLUMNS))})",
            [place_to_row(p) for p in places],
        )
        alias_rows = [
            (pid, alias, normalize_text(alias))
            for pid, values in aliases.items()
            for alias in values
        ]
        conn.executemany(
            "INSERT INTO aliases (place_id, alias, alias_norm) VALUES (?, ?, ?)",
            alias_rows,
        )
        conn.executemany(
            "INSERT INTO regions (id, name, kind, bbox_west, bbox_south, "
            "bbox_east, bbox_north, source, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    r.id,
                    r.name,
                    r.kind,
                    r.bbox.west if r.bbox else None,
                    r.bbox.south if r.bbox else None,
                    r.bbox.east if r.bbox else None,
                    r.bbox.north if r.bbox else None,
                    r.source,
                    r.note,
                )
                for r in regions
            ],
        )
        conn.executemany(
            "INSERT INTO catalog_meta (key, value) VALUES (?, ?)",
            list(meta.items()),
        )
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, path)
