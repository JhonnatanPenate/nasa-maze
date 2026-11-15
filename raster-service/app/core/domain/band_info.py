import math
from dataclasses import dataclass

from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class BandInfo:
    """One raster band: 1-based index, canonical name, unit and nodata
    sentinel (None when the file uses NaN or declares none)."""

    index: int
    name: str
    unit: str
    nodata: float | None

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
