from fastapi import APIRouter, Depends

from app.composition.dependencies import get_settings
from app.composition.profile_dependencies import get_analyze_profile
from app.core.config.settings import Settings
from app.core.domain.geo_point import GeoPoint
from app.features.profile_analysis.application.analyze_profile import (
    AnalyzeProfile,
)
from app.features.profile_analysis.presentation.profile_mapper import (
    ProfileMapper,
)
from app.features.profile_analysis.presentation.profile_schemas import (
    ProfileRequest,
    ProfileResponse,
)

router = APIRouter(prefix="/terrain", tags=["terrain"])


@router.post("/profile", response_model=ProfileResponse)
def analyze_profile(
    request: ProfileRequest,
    use_case: AnalyzeProfile = Depends(get_analyze_profile),
    settings: Settings = Depends(get_settings),
) -> ProfileResponse:
    path = [GeoPoint(lat=point.lat, lon=point.lon) for point in request.path]
    sample_distance_m = (
        request.sample_distance_m
        if request.sample_distance_m is not None
        else settings.sample_distance_m
    )
    profile = use_case.execute(path, sample_distance_m)
    return ProfileMapper.to_response(profile)
