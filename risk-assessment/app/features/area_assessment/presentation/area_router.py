from fastapi import APIRouter, Depends

from app.composition.dependencies import get_assess_area, get_settings
from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.local_solar_time import validate_hour
from app.core.errors.exceptions import DomainValidationError
from app.features.area_assessment.application.assess_area import AssessArea
from app.features.area_assessment.presentation.area_schemas import (
    AreaRequest,
    AreaResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/area", response_model=AreaResponse)
def assess_area(
    request: AreaRequest,
    use_case: AssessArea = Depends(get_assess_area),
    settings: Settings = Depends(get_settings),
) -> AreaResponse:
    """Plan extension: aggregate risk over a bbox (stub until Phase 5)."""
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in request.bbox)
        bbox = BoundingBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    except (TypeError, ValueError) as exc:
        raise DomainValidationError(f"Invalid bbox {request.bbox!r}") from exc
    try:
        validate_hour(request.hora)
    except ValueError as exc:
        raise DomainValidationError(str(exc)) from exc

    count = use_case.check_cap(bbox, request.max_cells)
    return AreaResponse(
        bbox=[bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat],
        cell_count=count,
        cell_size_m=None,
        level_counts={
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
            "unknown": 0,
        },
        blocked_fraction=None,
        mean_score=None,
        p95_score=None,
        factor_stats={},
        hotspots=[],
        aggregation="pending",
        note=(
            "Area aggregation is a plan extension pending Phase 5; the "
            "request was validated and capped but no cells were evaluated."
        ),
    )
