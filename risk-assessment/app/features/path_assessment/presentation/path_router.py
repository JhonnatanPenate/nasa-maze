from fastapi import APIRouter, Depends

from app.composition.dependencies import get_evaluate_path
from app.core.domain.geo_point import GeoPoint
from app.features.path_assessment.application.evaluate_path import EvaluatePath
from app.features.path_assessment.presentation.path_mapper import PathMapper
from app.features.path_assessment.presentation.path_schemas import (
    EvaluateRequest,
    EvaluateResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_path(
    request: EvaluateRequest,
    use_case: EvaluatePath = Depends(get_evaluate_path),
) -> EvaluateResponse:
    """SPEC §3.1/§4.1: risk evaluation along a polyline."""
    path = [GeoPoint(lat=p.lat, lon=p.lon) for p in request.path]
    result = use_case.execute(
        path=path,
        factors=tuple(request.factors) if request.factors is not None else None,
        sol=request.sol,
        hora=request.hora,
        sampling_step_m=request.sampling_step_m,
        vehicle_profile=request.vehicle_profile,
        speed_mps=request.speed_mps,
    )
    return PathMapper.to_response(result)
