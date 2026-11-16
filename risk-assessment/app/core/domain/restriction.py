"""Vehicle-profile traversal restrictions (plan §4.1, Javi ``celda_bloqueada``).

Restrictions are additive explanations reported next to the SPEC weighted
risk — they NEVER replace the computed score, force ``critical``, or turn a
missing factor into a safe one (plan §4.1/§4.3, SPEC §5).

Rules (all inherited Javi optimizer assumptions, configurable per profile):

- ``SLOPE_BLOCK``: MS4 ``slope_deg >= slope_block_deg`` (25 deg).
- ``TILT_BLOCK``: predicted ``tilt_deg >= tilt_block_deg`` (20 deg).
- ``TILT_MARGIN_BLOCK``: ``tilt_deg + tilt_margin_sigma * sigma >
  tilt_block_deg`` (Javi's ``inclinacion_con_margen > 20``, Z = 1.96).
- ``THERMAL_OUT_OF_BAND``: hourly ground-temp mean outside
  ``[thermal_min_K, thermal_max_K]`` — advisory only (``blocking=False``):
  Javi penalizes thermal excursions in the cost function but does not mark
  the cell impassable (DECISIONS MS5-D18).
"""

from dataclasses import dataclass

from app.core.domain.factor_catalog import (
    FACTOR_SLOPE,
    FACTOR_TEMPERATURE,
)
from app.core.domain.tilt_model import TiltPrediction
from app.core.domain.vehicle_profile import VehicleProfile


@dataclass(frozen=True)
class Restriction:
    """One profile-derived traversal restriction (plan §7.2 shape)."""

    code: str
    blocking: bool
    message: str
    factor: str
    value: float | None
    limit: float | None


def evaluate_restrictions(
    profile: VehicleProfile,
    *,
    slope_deg: float | None = None,
    tilt: TiltPrediction | None = None,
    temp_mean_K: float | None = None,
) -> tuple[Restriction, ...]:
    """Evaluate all profile rules for one sample; missing inputs simply
    skip their rule (nodata is not a violation)."""
    restrictions: list[Restriction] = []

    if slope_deg is not None and slope_deg >= profile.slope_block_deg:
        restrictions.append(
            Restriction(
                code="SLOPE_BLOCK",
                blocking=True,
                message=(
                    f"Slope {slope_deg:.1f} deg >= profile block limit "
                    f"{profile.slope_block_deg:.1f} deg"
                ),
                factor=FACTOR_SLOPE,
                value=slope_deg,
                limit=profile.slope_block_deg,
            )
        )

    if tilt is not None:
        if tilt.tilt_deg >= profile.tilt_block_deg:
            restrictions.append(
                Restriction(
                    code="TILT_BLOCK",
                    blocking=True,
                    message=(
                        f"Predicted tilt {tilt.tilt_deg:.1f} deg >= profile block "
                        f"limit {profile.tilt_block_deg:.1f} deg"
                    ),
                    factor="tilt",
                    value=tilt.tilt_deg,
                    limit=profile.tilt_block_deg,
                )
            )
        margin = tilt.tilt_deg + profile.tilt_margin_sigma * tilt.sigma
        if margin > profile.tilt_block_deg:
            restrictions.append(
                Restriction(
                    code="TILT_MARGIN_BLOCK",
                    blocking=True,
                    message=(
                        f"Tilt + {profile.tilt_margin_sigma}*sigma = {margin:.1f} deg "
                        f"> profile block limit {profile.tilt_block_deg:.1f} deg"
                    ),
                    factor="tilt",
                    value=margin,
                    limit=profile.tilt_block_deg,
                )
            )

    if temp_mean_K is not None and not (
        profile.thermal_min_K <= temp_mean_K <= profile.thermal_max_K
    ):
        restrictions.append(
            Restriction(
                code="THERMAL_OUT_OF_BAND",
                blocking=False,
                message=(
                    f"Ground temperature {temp_mean_K:.1f} K outside profile "
                    f"band [{profile.thermal_min_K:.0f}, {profile.thermal_max_K:.0f}] K"
                ),
                factor=FACTOR_TEMPERATURE,
                value=temp_mean_K,
                limit=None,
            )
        )

    return tuple(restrictions)
