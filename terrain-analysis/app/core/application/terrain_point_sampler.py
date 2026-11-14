import math

from app.core.application.terrain_point_sample import TerrainPointSample
from app.core.domain.geo_point import GeoPoint
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import NoCoverageError
from app.core.ports.terrain_repository import TerrainRepository


class TerrainPointSampler:
    """Shared application service: elevation + slope at one coordinate.

    Issues a single radius-1 `window_around` repository read; the window's
    centre cell provides the elevation and the 3x3 neighbourhood feeds the
    Horn's-method slope. A NaN centre elevation means no coverage; a valid
    centre whose slope stays NaN means no valid neighbouring cells.
    """

    def __init__(
        self,
        repository: TerrainRepository,
        slope_calculator: SlopeCalculator,
    ) -> None:
        self._repository = repository
        self._slope_calculator = slope_calculator

    def sample(self, point: GeoPoint) -> TerrainPointSample:
        window = self._repository.window_around(point, 1)
        elevation_m = window.center_value()
        if not math.isfinite(elevation_m):
            raise NoCoverageError(
                f"No DEM coverage at lat={point.lat}, lon={point.lon}"
            )
        try:
            slope_deg = self._slope_calculator.compute_at_center(window)
        except NoCoverageError as exc:
            raise NoCoverageError(
                f"Slope undefined at lat={point.lat}, lon={point.lon}: "
                f"no valid neighbouring cells"
            ) from exc
        return TerrainPointSample(
            elevation_m=elevation_m, slope_deg=slope_deg
        )
