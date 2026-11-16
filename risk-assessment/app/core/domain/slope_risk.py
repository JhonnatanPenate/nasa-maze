"""``slope`` factor scoring (SPEC §3.1/§5, plan §4.2).

Source: MS4 ``slope_deg``. Normalization is the SPEC's illustrative
baseline — 0 at ``<= score_floor_deg`` (5 deg), 1 at ``>= score_ceil_deg``
(30 deg), linear between. The warning threshold (15 deg) is Javi's
optimizer slope warning; the traversal block (25 deg) lives in the vehicle
profile, not here.
"""

from dataclasses import dataclass

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import FACTOR_SLOPE
from app.core.domain.normalization import linear_ramp


@dataclass(frozen=True)
class SlopeThresholds:
    score_floor_deg: float = 5.0  # SPEC §5 illustrative normalization
    score_ceil_deg: float = 30.0  # SPEC §5 illustrative normalization
    warning_deg: float = 15.0  # Javi optimizer slope warning (placeholder-free)


def assess_slope(
    slope_deg: float | None,
    thresholds: SlopeThresholds | None = None,
) -> FactorAssessment:
    """Score MS4 slope in degrees; ``None`` -> unavailable, never safe."""
    t = thresholds or SlopeThresholds()
    if slope_deg is None:
        return FactorAssessment(
            factor_id=FACTOR_SLOPE,
            available=False,
            observed={"slope_deg": None},
        )
    score = linear_ramp(slope_deg, t.score_floor_deg, t.score_ceil_deg)
    warnings: tuple[str, ...] = ()
    if slope_deg >= t.warning_deg:
        warnings = (f"STEEP_SLOPE_{round(slope_deg)}DEG",)
    return FactorAssessment(
        factor_id=FACTOR_SLOPE,
        available=True,
        score=score,
        warnings=warnings,
        observed={"slope_deg": slope_deg},
    )
