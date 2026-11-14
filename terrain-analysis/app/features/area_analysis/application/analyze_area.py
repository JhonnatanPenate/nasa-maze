import math

import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
)
from app.core.ports.terrain_repository import TerrainRepository
from app.features.area_analysis.domain.area_stats import AreaStats
from app.features.area_analysis.domain.value_stats import ValueStats


class AnalyzeArea:
    """Use case F4: aggregate elevation/slope statistics over a bbox.

    Depends only on the TerrainRepository port and domain services.
    Coverage/limits errors raised by the repository (NoCoverageError,
    DomainValidationError, UpstreamDatasourceError) propagate unchanged.
    """

    def __init__(
        self,
        repository: TerrainRepository,
        slope_calculator: SlopeCalculator,
        steep_min_deg: float,
    ) -> None:
        try:
            threshold = float(steep_min_deg)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                f"steep_min_deg must be numeric, got {steep_min_deg!r}"
            ) from exc
        if not math.isfinite(threshold):
            raise DomainValidationError(
                f"steep_min_deg must be finite, got {threshold}"
            )
        self._repository = repository
        self._slope_calculator = slope_calculator
        self._steep_min_deg = threshold

    def execute(self, bbox: BoundingBox) -> AreaStats:
        # A 1-cell halo supplies real DEM neighbours for the border cells
        # of the bbox window, so their Horn slope equals an interior
        # computation instead of relying on mirror extrapolation.
        halo = self._repository.window_for_with_halo(bbox, halo_cells=1)
        core = halo.core()
        # window_for on an all-nodata bbox returns an all-NaN window
        # instead of raising; treat it as no coverage.
        if core.is_all_nodata():
            raise NoCoverageError(
                "Requested bounding box covers only nodata cells"
            )
        slopes = self._slope_calculator.compute(halo.window)
        core_slopes = slopes[halo.core_rows, halo.core_cols]
        valid_slopes = core_slopes[~np.isnan(core_slopes)]
        if valid_slopes.size == 0:
            raise NoCoverageError(
                "Requested bounding box contains no cells with "
                "computable slope"
            )
        return AreaStats(
            elevation_m=ValueStats(
                min=float(np.nanmin(core.elevation)),
                max=float(np.nanmax(core.elevation)),
                mean=float(np.nanmean(core.elevation)),
            ),
            slope_deg=ValueStats(
                min=float(valid_slopes.min()),
                max=float(valid_slopes.max()),
                mean=float(valid_slopes.mean()),
            ),
            steep_fraction=(
                float(np.count_nonzero(valid_slopes >= self._steep_min_deg))
                / valid_slopes.size
            ),
        )
