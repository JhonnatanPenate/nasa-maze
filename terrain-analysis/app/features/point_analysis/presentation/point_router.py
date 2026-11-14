from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.composition.point_dependencies import get_analyze_point
from app.core.domain.geo_point import GeoPoint
from app.features.point_analysis.application.analyze_point import AnalyzePoint
from app.features.point_analysis.presentation.point_mapper import PointMapper
from app.features.point_analysis.presentation.point_schemas import (
    PointAnalysisResponse,
)

router = APIRouter(prefix="/terrain", tags=["terrain"])


@router.get("/point", response_model=PointAnalysisResponse)
def analyze_point(
    lat: Annotated[
        float, Query(description="Planetocentric latitude")
    ],
    lon: Annotated[
        float,
        Query(description="Planetocentric longitude"),
    ],
    body: Annotated[
        str,
        Query(
            description=(
                "Celestial body label. Accepted for contract compatibility; "
                "the MVP serves a single configured DEM and ignores it."
            )
        ),
    ] = "mars",
    use_case: AnalyzePoint = Depends(get_analyze_point),
) -> PointAnalysisResponse:
    result = use_case.execute(GeoPoint(lat=lat, lon=lon))
    return PointMapper.to_response(result)
