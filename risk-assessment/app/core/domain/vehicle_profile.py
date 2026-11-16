"""Vehicle profile domain object (plan extension — config/vehicle_profiles.yaml).

Values are inherited Javi optimizer assumptions for a generic Gale rover —
not certified flight limits (plan §13.3). Restrictions derived from a profile
are reported separately and never override the SPEC weighted risk.
"""

from dataclasses import dataclass

from app.core.domain.soil_type import SoilType


@dataclass(frozen=True)
class VehicleProfile:
    name: str
    description: str
    nominal_speed_m_h: float
    tilt_speed_factor: str  # human-readable formula note (see tilt_speed_*)
    dune_speed_factor: float
    slope_block_deg: float
    tilt_block_deg: float
    tilt_margin_sigma: float
    thermal_min_K: float
    thermal_max_K: float
    dose_budget_uGy: float | None
    # Javi motion-model constants (optimizador_rutas.py:44-48):
    # VELOCIDAD_MAXIMA_M_H nominal; speed -> floor at tilt >= limit;
    # arena_dunas cells multiply by (1 - FACTOR_DESLIZAMIENTO_ARENA) = 0.40.
    tilt_speed_limit_deg: float = 30.0
    tilt_speed_floor: float = 0.1


def effective_speed_m_h(
    profile: VehicleProfile,
    *,
    tilt_deg: float | None,
    soil: SoilType | None,
) -> float:
    """Javi ``velocidad_efectiva``: ``nominal * max(floor, 1 - tilt/limit)``,
    times ``dune_speed_factor`` on ``arena_dunas`` cells.

    ``tilt_deg=None`` (nodata predictors) falls back to the unpenalized
    nominal speed — an assumption, documented in DECISIONS MS5-D18.
    """
    tilt = 0.0 if tilt_deg is None else tilt_deg
    factor = max(
        profile.tilt_speed_floor,
        1.0 - tilt / profile.tilt_speed_limit_deg,
    )
    speed = profile.nominal_speed_m_h * factor
    if soil == SoilType.ARENA_DUNAS:
        speed *= profile.dune_speed_factor
    return speed


def travel_hours(distance_m: float, speed_m_h: float) -> float:
    """Elapsed hours for ``distance_m`` at ``speed_m_h`` (Javi's m/h clock)."""
    if speed_m_h <= 0.0:
        raise ValueError(f"speed_m_h must be positive, got {speed_m_h}")
    return distance_m / speed_m_h
