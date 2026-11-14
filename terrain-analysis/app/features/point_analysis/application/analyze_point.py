import math

from app.core.domain.geo_point import GeoPoint
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.errors.exceptions import NoCoverageError
from app.core.ports.terrain_repository import TerrainRepository
from app.features.point_analysis.domain.point_analysis import PointAnalysis


class AnalyzePoint:
    """Use case: elevation, slope and terrain class at one coordinate.

    A single radius-1 DEM window read feeds both the elevation sample and
    the Horn's-method slope at the cell containing the point.
    """

    def __init__(
        self,
        repository: TerrainRepository,
        slope_calculator: SlopeCalculator,
        classifier: TerrainClassifier,
    ) -> None:
        self._repository = repository
        self._slope_calculator = slope_calculator
        self._classifier = classifier

    def execute(self, point: GeoPoint) -> PointAnalysis:
        window = self._repository.window_around(point, 1)
        elevation_m = window.center_value()
        if not math.isfinite(elevation_m):
            raise NoCoverageError(
                f"No DEM coverage at lat={point.lat}, lon={point.lon}"
            )
        slope_deg = self._slope_calculator.compute_at_center(window)
        return PointAnalysis(
            lat=point.lat,
            lon=point.lon,
            elevation_m=elevation_m,
            slope_deg=slope_deg,
            terrain_class=self._classifier.classify(slope_deg),
        )
