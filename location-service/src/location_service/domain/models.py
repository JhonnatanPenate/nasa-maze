"""Canonical domain models (README section 3.3). Pure dataclasses, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from location_service.domain.geo import BboxTuple, bbox_contains


@dataclass(frozen=True)
class Coordinate:
    """A validated Mars coordinate. lon is always normalized to [0, 360)."""

    lat: float
    lon: float


@dataclass(frozen=True)
class Bbox:
    """Bounding box (west, south, east, north); longitudes in [0, 360)."""

    west: float
    south: float
    east: float
    north: float

    def as_tuple(self) -> BboxTuple:
        return (self.west, self.south, self.east, self.north)

    def contains(self, lat: float, lon: float) -> bool:
        return bbox_contains(self.as_tuple(), lat, lon)


@dataclass(frozen=True)
class Place:
    """A named Martian place (Gazetteer feature, mission POI or landing site)."""

    id: str
    name: str
    body: str
    kind: str  # feature | poi | landing_site
    feature_type: str
    source: str  # iau_gazetteer | mission_msl | config
    center: Coordinate
    name_clean: str | None = None
    name_norm: str = ""
    bbox: Bbox | None = None
    diameter_km: float | None = None
    elevation_m: float | None = None
    approval_status: str | None = None
    origin: str | None = None
    tags: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Region:
    """A known region / area of interest (indicative static bbox)."""

    id: str
    name: str
    kind: str
    source: str
    bbox: Bbox | None = None
    note: str | None = None
