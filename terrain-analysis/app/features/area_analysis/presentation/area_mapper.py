from app.core.domain.bounding_box import BoundingBox
from app.features.area_analysis.domain.area_stats import AreaStats
from app.features.area_analysis.presentation.area_schemas import (
    AreaResponse,
    ValueStatsResponse,
)


class AreaMapper:
    """Adapters between the HTTP DTOs and area_analysis domain objects."""

    @staticmethod
    def to_bounding_box(bbox: list[float]) -> BoundingBox:
        return BoundingBox(
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
        )

    @staticmethod
    def to_response(stats: AreaStats) -> AreaResponse:
        return AreaResponse(
            elevation_m=ValueStatsResponse(
                min=stats.elevation_m.min,
                max=stats.elevation_m.max,
                mean=stats.elevation_m.mean,
            ),
            slope_deg=ValueStatsResponse(
                min=stats.slope_deg.min,
                max=stats.slope_deg.max,
                mean=stats.slope_deg.mean,
            ),
            steep_fraction=stats.steep_fraction,
        )
