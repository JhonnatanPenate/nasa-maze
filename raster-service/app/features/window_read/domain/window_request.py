from dataclasses import dataclass

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class WindowRequest:
    """Validated body of `POST /raster/{dataset}/window` (spec §3.4).

    Exactly one selection form: `bbox` (optionally expanded by
    `halo_cells`) or `point` + `radius_cells`. On point reads
    `halo_cells` is meaningless and normalised to 0; `radius_cells` is
    ignored on bbox reads. Violations raise RasterValidationError so
    they surface as 400, not 422.
    """

    band: str
    bbox: BoundingBox | None = None
    point: GeoPoint | None = None
    halo_cells: int = 0
    radius_cells: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.band, str) or not self.band:
            raise RasterValidationError(
                f"WindowRequest band must be a non-empty string, "
                f"got {self.band!r}"
            )
        if self.bbox is not None and not isinstance(self.bbox, BoundingBox):
            raise RasterValidationError(
                f"WindowRequest bbox must be a BoundingBox, "
                f"got {self.bbox!r}"
            )
        if self.point is not None and not isinstance(self.point, GeoPoint):
            raise RasterValidationError(
                f"WindowRequest point must be a GeoPoint, "
                f"got {self.point!r}"
            )
        if (self.bbox is None) == (self.point is None):
            raise RasterValidationError(
                "WindowRequest needs exactly one of 'bbox' and 'point'"
            )
        if self.point is not None:
            # halo_cells is ignored on point reads (spec §3.4).
            object.__setattr__(self, "halo_cells", 0)
            if self.radius_cells is None:
                raise RasterValidationError(
                    "'radius_cells' is required with 'point'"
                )
            self._check_count("radius_cells", self.radius_cells)
        else:
            self._check_count("halo_cells", self.halo_cells)

    @staticmethod
    def _check_count(name: str, value: int) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise RasterValidationError(
                f"{name} must be an integer >= 0, got {value!r}"
            )
