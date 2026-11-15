import math
from dataclasses import dataclass

from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class BandInfo:
    """One raster band: 1-based index, canonical name, unit, nodata
    sentinel (None when the file uses NaN or declares none), plus render
    config merged from the registry (colormap name and display
    value_range for the PNG layer; "" / None when unset)."""

    index: int
    name: str
    unit: str
    nodata: float | None
    colormap: str = ""
    value_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 1:
            raise RasterValidationError(
                f"BandInfo index must be a positive int, got {self.index!r}"
            )
        if not isinstance(self.name, str) or not self.name:
            raise RasterValidationError(
                f"BandInfo name must be a non-empty string, got {self.name!r}"
            )
        if self.nodata is not None:
            try:
                nodata = float(self.nodata)
            except (TypeError, ValueError) as exc:
                raise RasterValidationError(
                    f"BandInfo nodata must be numeric or None, got {self.nodata!r}"
                ) from exc
            if math.isnan(nodata):
                nodata = None
            elif not math.isfinite(nodata):
                raise RasterValidationError(
                    f"BandInfo nodata must be finite, got {nodata}"
                )
            object.__setattr__(self, "nodata", nodata)
        if not isinstance(self.colormap, str):
            raise RasterValidationError(
                f"BandInfo colormap must be a string, got {self.colormap!r}"
            )
        if self.value_range is not None:
            try:
                low, high = self.value_range
                value_range = (float(low), float(high))
            except (TypeError, ValueError) as exc:
                raise RasterValidationError(
                    f"BandInfo value_range must be a (min, max) pair, "
                    f"got {self.value_range!r}"
                ) from exc
            if not all(math.isfinite(v) for v in value_range):
                raise RasterValidationError(
                    f"BandInfo value_range must be finite, "
                    f"got {value_range}"
                )
            if not value_range[0] < value_range[1]:
                raise RasterValidationError(
                    f"BandInfo value_range min must be less than max, "
                    f"got {value_range}"
                )
            object.__setattr__(self, "value_range", value_range)
