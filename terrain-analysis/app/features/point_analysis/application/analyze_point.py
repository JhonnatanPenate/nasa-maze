from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.domain.geo_point import GeoPoint
from app.core.domain.terrain_classifier import TerrainClassifier
from app.features.point_analysis.domain.point_analysis import PointAnalysis


class AnalyzePoint:
    """Use case: elevation, slope and terrain class at one coordinate.

    The shared TerrainPointSampler performs the single radius-1 DEM
    window read that feeds both the elevation sample and the
    Horn's-method slope at the cell containing the point.
    """

    def __init__(
        self,
        sampler: TerrainPointSampler,
        classifier: TerrainClassifier,
    ) -> None:
        self._sampler = sampler
        self._classifier = classifier

    def execute(self, point: GeoPoint) -> PointAnalysis:
        sample = self._sampler.sample(point)
        return PointAnalysis(
            lat=point.lat,
            lon=point.lon,
            elevation_m=sample.elevation_m,
            slope_deg=sample.slope_deg,
            terrain_class=self._classifier.classify(sample.slope_deg),
        )
