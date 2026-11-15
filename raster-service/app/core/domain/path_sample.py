from dataclasses import dataclass

from app.core.domain.geo_point import GeoPoint


@dataclass(frozen=True)
class PathSample:
    point: GeoPoint
    distance_m: float
