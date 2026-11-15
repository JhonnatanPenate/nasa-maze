import math
from dataclasses import dataclass

from app.core.domain.band_info import BandInfo
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.grid_geometry import GridGeometry
from app.core.errors.exceptions import RasterValidationError, UnknownBandError


@dataclass(frozen=True)
class DatasetMetadata:
    """Domain-facing description of a registered raster dataset."""

    name: str
    crs: str
    bounds: BoundingBox
    width: int
    height: int
    resolution_m: float
    bands: tuple[BandInfo, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise RasterValidationError(
                f"DatasetMetadata name must be a non-empty string, got {self.name!r}"
            )
        for name in ("width", "height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise RasterValidationError(
                    f"DatasetMetadata {name} must be a positive int, got {value!r}"
                )
        for name in ("resolution_m",):
            try:
                value = float(getattr(self, name))
            except (TypeError, ValueError) as exc:
                raise RasterValidationError(
                    f"DatasetMetadata {name} must be numeric, "
                    f"got {getattr(self, name)!r}"
                ) from exc
            if not math.isfinite(value) or value <= 0.0:
                raise RasterValidationError(
                    f"DatasetMetadata {name} must be a positive finite number, "
                    f"got {value}"
                )
            object.__setattr__(self, name, value)
        if not self.bands:
            raise RasterValidationError(
                "DatasetMetadata needs at least one band"
            )
        names = [band.name for band in self.bands]
        if len(set(names)) != len(names):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            raise RasterValidationError(
                f"DatasetMetadata band names must be unique, "
                f"duplicates: {', '.join(duplicates)}"
            )

    @property
    def res_lon_deg(self) -> float:
        return (self.bounds.max_lon - self.bounds.min_lon) / self.width

    @property
    def res_lat_deg(self) -> float:
        return (self.bounds.max_lat - self.bounds.min_lat) / self.height

    def band(self, name: str) -> BandInfo:
        for band in self.bands:
            if band.name == name:
                return band
        raise UnknownBandError(
            f"Unknown band {name!r} for dataset {self.name!r}. "
            f"Valid bands: {', '.join(self.band_names())}"
        )

    def band_names(self) -> list[str]:
        return [band.name for band in self.bands]

    def grid_geometry(self) -> GridGeometry:
        return GridGeometry(self.bounds, rows=self.height, cols=self.width)
