from app.core.domain.vehicle_profile import VehicleProfile
from app.features.vehicle_profiles.presentation.vehicle_profile_schemas import (
    VehicleProfileSchema,
)


class VehicleProfileMapper:
    @staticmethod
    def to_schema(profile: VehicleProfile) -> VehicleProfileSchema:
        return VehicleProfileSchema(
            name=profile.name,
            description=profile.description,
            nominal_speed_m_h=profile.nominal_speed_m_h,
            tilt_speed_factor=profile.tilt_speed_factor,
            dune_speed_factor=profile.dune_speed_factor,
            slope_block_deg=profile.slope_block_deg,
            tilt_block_deg=profile.tilt_block_deg,
            tilt_margin_sigma=profile.tilt_margin_sigma,
            thermal_min_K=profile.thermal_min_K,
            thermal_max_K=profile.thermal_max_K,
            dose_budget_uGy=profile.dose_budget_uGy,
        )
