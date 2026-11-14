from app.features.point_analysis.domain.point_analysis import PointAnalysis
from app.features.point_analysis.presentation.point_schemas import (
    PointAnalysisResponse,
)


class PointMapper:
    """Domain -> DTO adapter for point analysis results."""

    @staticmethod
    def to_response(analysis: PointAnalysis) -> PointAnalysisResponse:
        return PointAnalysisResponse(
            lat=analysis.lat,
            lon=analysis.lon,
            elevation_m=analysis.elevation_m,
            slope_deg=analysis.slope_deg,
            terrain_class=analysis.terrain_class,
        )
