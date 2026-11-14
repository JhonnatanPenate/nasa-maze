import math
from dataclasses import dataclass

from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import DomainValidationError

_LAT_RANGE = (-90.0, 90.0)
_LON_RANGE = (-180.0, 180.0)


@dataclass(frozen=True)
class BoundingBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def __post_init__(self) -> None:
        values = {}
        for name in ("min_lon", "min_lat", "max_lon", "max_lat"):
            try:
                values[name] = float(getattr(self, name))
            except (TypeError, ValueError) as exc:
                raise DomainValidationError(
                    f"BoundingBox field {name} must be numeric, "
                    f"got {getattr(self, name)!r}"
                ) from exc
            if not math.isfinite(values[name]):
                raise DomainValidationError(
                    f"BoundingBox field {name} must be finite, got {values[name]}"
                )
            object.__setattr__(self, name, values[name])
        for name in ("min_lat", "max_lat"):
            if not (_LAT_RANGE[0] <= values[name] <= _LAT_RANGE[1]):
                raise DomainValidationError(
                    f"BoundingBox {name}={values[name]} out of range {_LAT_RANGE}"
                )
        for name in ("min_lon", "max_lon"):
            if not (_LON_RANGE[0] <= values[name] <= _LON_RANGE[1]):
                raise DomainValidationError(
                    f"BoundingBox {name}={values[name]} out of range {_LON_RANGE}"
                )
        if self.min_lon >= self.max_lon:
            raise DomainValidationError(
                f"BoundingBox min_lon ({self.min_lon}) must be less than "
                f"max_lon ({self.max_lon})"
            )
        if self.min_lat >= self.max_lat:
            raise DomainValidationError(
                f"BoundingBox min_lat ({self.min_lat}) must be less than "
                f"max_lat ({self.max_lat})"
            )

    def contains(self, point: GeoPoint) -> bool:
        return (
            self.min_lat <= point.lat <= self.max_lat
            and self.min_lon <= point.lon <= self.max_lon
        )
