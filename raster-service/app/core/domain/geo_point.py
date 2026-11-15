import math
from dataclasses import dataclass

from app.core.errors.exceptions import RasterValidationError

_LAT_RANGE = (-90.0, 90.0)
_LON_RANGE = (-180.0, 180.0)


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        try:
            lat = float(self.lat)
            lon = float(self.lon)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"GeoPoint coordinates must be numeric, got lat={self.lat!r}, lon={self.lon!r}"
            ) from exc
        object.__setattr__(self, "lat", lat)
        object.__setattr__(self, "lon", lon)
        if not math.isfinite(lat) or not (_LAT_RANGE[0] <= lat <= _LAT_RANGE[1]):
            raise RasterValidationError(
                f"Latitude {lat} out of range {_LAT_RANGE}"
            )
        if not math.isfinite(lon) or not (_LON_RANGE[0] <= lon <= _LON_RANGE[1]):
            raise RasterValidationError(
                f"Longitude {lon} out of range {_LON_RANGE}"
            )
