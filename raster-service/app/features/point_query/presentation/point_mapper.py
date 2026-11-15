import math

from app.features.point_query.domain.point_values import PointValues
from app.features.point_query.presentation.point_schemas import (
    PointResponse,
)


class PointMapper:
    """Domain -> DTO adapter for point queries (NaN -> null on the wire)."""

    @staticmethod
    def to_response(result: PointValues) -> PointResponse:
        return PointResponse(
            lat=result.point.lat,
            lon=result.point.lon,
            values={
                name: (None if math.isnan(value) else value)
                for name, value in result.values.items()
            },
        )
