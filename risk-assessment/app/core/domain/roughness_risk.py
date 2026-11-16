"""``roughness`` factor scoring (SPEC §3.1/§5, plan §4.2).

Source: MS3 band ``rugosidad_m`` (surface roughness in metres). Javi's
``<=0.60`` / ``>=1.10`` values are soil-classification regimes, not a
published risk scale — the score ramp and warning threshold are
``placeholder`` values pending calibration (DECISIONS.md MS5-D14).
"""

from dataclasses import dataclass

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import FACTOR_ROUGHNESS
from app.core.domain.normalization import linear_ramp


@dataclass(frozen=True)
class RoughnessThresholds:
    score_floor_m: float = 0.5  # placeholder (DECISIONS MS5-D14)
    score_ceil_m: float = 3.0  # placeholder (DECISIONS MS5-D14)
    warning_m: float = 1.5  # placeholder -> HIGH_ROUGHNESS (DECISIONS MS5-D14)


def assess_roughness(
    rugosidad_m: float | None,
    thresholds: RoughnessThresholds | None = None,
) -> FactorAssessment:
    """Score surface roughness; ``None`` (nodata) -> unavailable."""
    t = thresholds or RoughnessThresholds()
    if rugosidad_m is None:
        return FactorAssessment(
            factor_id=FACTOR_ROUGHNESS,
            available=False,
            observed={"rugosidad_m": None},
        )
    score = linear_ramp(rugosidad_m, t.score_floor_m, t.score_ceil_m)
    warnings = ("HIGH_ROUGHNESS",) if rugosidad_m >= t.warning_m else ()
    return FactorAssessment(
        factor_id=FACTOR_ROUGHNESS,
        available=True,
        score=score,
        warnings=warnings,
        observed={"rugosidad_m": rugosidad_m},
    )
