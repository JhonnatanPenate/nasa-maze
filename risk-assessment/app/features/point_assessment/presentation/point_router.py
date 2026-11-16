from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.composition.dependencies import get_assess_point
from app.core.domain.geo_point import GeoPoint
from app.features.point_assessment.application.assess_point import AssessPoint
from app.features.point_assessment.presentation.point_mapper import PointMapper
from app.features.point_assessment.presentation.point_schemas import (
    PointRiskResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/point", response_model=PointRiskResponse)
def assess_point(
    lat: Annotated[float, Query(description="Planetocentric latitude")],
    lon: Annotated[float, Query(description="Planetocentric longitude")],
    sol: Annotated[
        int | None,
        Query(description="Reference sol for environmental profiles"),
    ] = None,
    hora: Annotated[
        int | None,
        Query(description="LMST hour 0-23; omit to evaluate all hours"),
    ] = None,
    include_hourly: Annotated[
        bool,
        Query(description="Include per-hour breakdown when hora is omitted"),
    ] = False,
    factors: Annotated[
        str | None,
        Query(description="Comma-separated subset of the factor catalog"),
    ] = None,
    body: Annotated[
        str,
        Query(description="Celestial body; only 'mars' is served"),
    ] = "mars",
    use_case: AssessPoint = Depends(get_assess_point),
) -> PointRiskResponse:
    """SPEC §3.2/§4.2: risk at a single point."""
    point = GeoPoint(lat=lat, lon=lon)
    factor_tuple = tuple(f.strip() for f in factors.split(",") if f.strip()) if factors else None
    result = use_case.execute(
        point=point,
        sol=sol,
        hora=hora,
        include_hourly=include_hourly,
        factors=factor_tuple,
    )
    return PointMapper.to_response(result)
