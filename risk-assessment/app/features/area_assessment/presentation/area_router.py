from fastapi import APIRouter, Depends

from app.composition.dependencies import get_assess_area
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.local_solar_time import validate_hour
from app.core.errors.exceptions import DomainValidationError
from app.features.area_assessment.application.assess_area import AssessArea
from app.features.area_assessment.domain.area_result import AreaResult
from app.features.area_assessment.presentation.area_schemas import (
    AreaRequest,
    AreaResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/area", response_model=AreaResponse)
def assess_area(
    request: AreaRequest,
    use_case: AssessArea = Depends(get_assess_area),
) -> AreaResponse:
    """Plan extension: aggregate SPEC risk over a bbox grid (Phase 5)."""
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in request.bbox)
        bbox = BoundingBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(f"Invalid bbox {request.bbox!r}") from exc
    try:
        validate_hour(request.hora)
    except ValueError as exc:
        raise DomainValidationError(str(exc)) from exc

    result = use_case.execute(
        bbox=bbox,
        sol=request.sol,
        hora=request.hora,
        vehicle_profile=request.vehicle_profile,
        max_cells=request.max_cells,
    )
    return _to_response(result)


def _to_response(result: AreaResult) -> AreaResponse:
    return AreaResponse(
        bbox=[result.bbox[0], result.bbox[1], result.bbox[2], result.bbox[3]],
        cell_count=result.cell_count,
        cell_size_m=result.cell_size_m,
        level_counts=result.level_counts,
        blocked_fraction=result.blocked_fraction,
        mean_score=result.mean_score,
        p95_score=result.p95_score,
        factor_stats=result.factor_stats,
        hotspots=list(result.hotspots),
        aggregation=result.aggregation,
        note=result.note,
        confidence=result.confidence,
        uncovered_cells=result.uncovered_cells,
        provenance=result.provenance,
        data_quality_notes=list(result.data_quality_notes),
    )
