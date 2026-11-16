from pydantic import BaseModel


class VehicleProfileSchema(BaseModel):
    """Additive plan extension — mirrors config/vehicle_profiles.yaml."""

    name: str
    description: str
    nominal_speed_m_h: float
    tilt_speed_factor: str
    dune_speed_factor: float
    slope_block_deg: float
    tilt_block_deg: float
    tilt_margin_sigma: float
    thermal_min_K: float
    thermal_max_K: float
    dose_budget_uGy: float | None


class VehicleProfilesResponse(BaseModel):
    profiles: list[VehicleProfileSchema]
    default: str
    note: str | None = None
