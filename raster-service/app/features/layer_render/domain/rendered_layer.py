import math
from dataclasses import dataclass

from app.core.domain.bounding_box import BoundingBox
from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class RenderedLayer:
    """A rendered PNG layer plus the georeferencing needed to overlay
    it on a map: dataset extent, CRS label and the (min, max) value
    range the colours were stretched over (equal for constant bands)."""

    png: bytes
    bounds: BoundingBox
    crs: str
    value_range: tuple[float, float]

    def __post_init__(self) -> None:
        if not isinstance(self.png, bytes) or not self.png:
            raise RasterValidationError(
                "RenderedLayer png must be non-empty bytes"
            )
        if not isinstance(self.bounds, BoundingBox):
            raise RasterValidationError(
                f"RenderedLayer bounds must be a BoundingBox, "
                f"got {self.bounds!r}"
            )
        if not isinstance(self.crs, str) or not self.crs:
            raise RasterValidationError(
                f"RenderedLayer crs must be a non-empty string, "
                f"got {self.crs!r}"
            )
        try:
            low, high = self.value_range
            value_range = (float(low), float(high))
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"RenderedLayer value_range must be a (min, max) pair, "
                f"got {self.value_range!r}"
            ) from exc
        if not all(math.isfinite(v) for v in value_range):
            raise RasterValidationError(
                f"RenderedLayer value_range must be finite, "
                f"got {value_range}"
            )
        if value_range[0] > value_range[1]:
            raise RasterValidationError(
                f"RenderedLayer value_range min must not exceed max, "
                f"got {value_range}"
            )
        object.__setattr__(self, "value_range", value_range)
