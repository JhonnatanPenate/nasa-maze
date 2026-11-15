import math

from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError


class DistanceCalculator:
    """Haversine distance and linear interpolation on a spherical body."""

    def __init__(self, radius_m: float) -> None:
        try:
            radius = float(radius_m)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"Body radius must be numeric, got {radius_m!r}"
            ) from exc
        if not math.isfinite(radius) or radius <= 0.0:
            raise RasterValidationError(
                f"Body radius must be a positive finite number, got {radius}"
            )
        self._radius_m = radius

    @property
    def radius_m(self) -> float:
        return self._radius_m

    def distance_m(self, a: GeoPoint, b: GeoPoint) -> float:
        lat1 = math.radians(a.lat)
        lat2 = math.radians(b.lat)
        dlat = lat2 - lat1
        dlon = math.radians(b.lon - a.lon)
        h = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
        )
        return 2.0 * self._radius_m * math.asin(min(1.0, math.sqrt(h)))

    def interpolate(self, a: GeoPoint, b: GeoPoint, fraction: float) -> GeoPoint:
        try:
            f = float(fraction)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"Interpolation fraction must be numeric, got {fraction!r}"
            ) from exc
        if not math.isfinite(f) or f < 0.0 or f > 1.0:
            raise RasterValidationError(
                f"Interpolation fraction must be in [0, 1], got {f}"
            )
        return GeoPoint(
            lat=a.lat + (b.lat - a.lat) * f,
            lon=a.lon + (b.lon - a.lon) * f,
        )
