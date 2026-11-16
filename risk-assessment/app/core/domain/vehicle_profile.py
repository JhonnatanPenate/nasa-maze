"""Vehicle profile domain object (plan extension — config/vehicle_profiles.yaml).

Values are inherited Javi optimizer assumptions for a generic Gale rover —
not certified flight limits (plan §13.3). Restrictions derived from a profile
are reported separately and never override the SPEC weighted risk.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleProfile:
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
