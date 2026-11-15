from dataclasses import dataclass

from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class PointValues:
    """Verbatim band values at one coordinate.

    NaN is the in-domain nodata marker; the presentation mapper converts
    it to null on the wire (D5).
    """

    point: GeoPoint
    values: dict[str, float]

    def __post_init__(self) -> None:
        if not isinstance(self.values, dict) or not self.values:
            raise RasterValidationError(
                "PointValues needs a non-empty band->value mapping"
            )
        for name, value in self.values.items():
            if not isinstance(name, str) or not name:
                raise RasterValidationError(
                    f"PointValues band names must be non-empty strings, "
                    f"got {name!r}"
                )
            self.values[name] = float(value)
