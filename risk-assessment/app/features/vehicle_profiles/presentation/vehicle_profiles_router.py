from fastapi import APIRouter, Depends

from app.composition.dependencies import (
    get_settings,
    list_vehicle_profiles,
)
from app.core.config.settings import Settings
from app.features.vehicle_profiles.application.list_vehicle_profiles import (
    ListVehicleProfiles,
)
from app.features.vehicle_profiles.presentation.vehicle_profile_mapper import (
    VehicleProfileMapper,
)
from app.features.vehicle_profiles.presentation.vehicle_profile_schemas import (
    VehicleProfilesResponse,
)

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/vehicle-profiles", response_model=VehicleProfilesResponse)
def get_vehicle_profiles(
    use_case: ListVehicleProfiles = Depends(list_vehicle_profiles),
    settings: Settings = Depends(get_settings),
) -> VehicleProfilesResponse:
    """Plan extension: configured vehicle profiles and limits."""
    profiles = use_case.execute()
    return VehicleProfilesResponse(
        profiles=[VehicleProfileMapper.to_schema(p) for p in profiles],
        default=settings.default_vehicle_profile,
        note=(
            "Inherited optimizer assumptions for a generic Gale rover "
            "profile, not certified flight limits."
        ),
    )
