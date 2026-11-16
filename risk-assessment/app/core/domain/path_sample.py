from dataclasses import dataclass

from app.core.domain.geo_point import GeoPoint


@dataclass(frozen=True)
class PathSample:
    """One arc-length sample along a polyline (same convention as MS3/MS4)."""

    point: GeoPoint
    distance_m: float
