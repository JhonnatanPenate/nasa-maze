from fastapi import APIRouter, Depends

from app.composition.area_dependencies import get_analyze_area
from app.features.area_analysis.application.analyze_area import AnalyzeArea
from app.features.area_analysis.presentation.area_mapper import AreaMapper
from app.features.area_analysis.presentation.area_schemas import (
    AreaRequest,
    AreaResponse,
)

router = APIRouter(prefix="/terrain", tags=["terrain"])


@router.post("/area", response_model=AreaResponse)
def analyze_area(
    request: AreaRequest,
    use_case: AnalyzeArea = Depends(get_analyze_area),
) -> AreaResponse:
    stats = use_case.execute(AreaMapper.to_bounding_box(request.bbox))
    return AreaMapper.to_response(stats)
