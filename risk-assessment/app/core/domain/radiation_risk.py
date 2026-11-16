"""``radiation`` factor scoring (SPEC §3.1/§5, plan §4.2).

Source: RAD hourly **dose-E rate** (``dosis_e_uGy_h``, uGy/h) selected by
the nearest RAD sol and LMST hour. MS5 reports a *rate* only — route dose
accumulation belongs to MS6 (SPEC §8). Dose-B is provenance, never
combined.

Score = ``dose / score_full_scale_uGy_h`` clipped to [0, 1]
(``placeholder`` normalization — DECISIONS MS5-D17). The ingest-time
``0.7 * median`` filter is Javi's background-profile rule, NOT a warning
threshold; ``HIGH_RADIATION_RATE`` uses the configurable
``warning_uGy_h`` (placeholder, DECISIONS MS5-D17).
"""

from dataclasses import dataclass

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import FACTOR_RADIATION
from app.core.domain.normalization import clamp01


@dataclass(frozen=True)
class RadiationThresholds:
    warning_uGy_h: float = 20.0  # placeholder (DECISIONS MS5-D17)
    score_full_scale_uGy_h: float = 30.0  # placeholder (DECISIONS MS5-D17)


def assess_radiation(
    dose_e_uGy_h: float | None,
    *,
    dose_b_uGy_h: float | None = None,
    unit: str | None = None,
    provenance: str | None = None,
    thresholds: RadiationThresholds | None = None,
) -> FactorAssessment:
    """Score the hourly dose-E rate; ``None`` -> unavailable."""
    t = thresholds or RadiationThresholds()
    observed = {
        "dose_e_uGy_h": dose_e_uGy_h,
        "dose_b_uGy_h": dose_b_uGy_h,
        "unit": unit,
        "provenance": provenance,
    }
    if dose_e_uGy_h is None:
        return FactorAssessment(
            factor_id=FACTOR_RADIATION,
            available=False,
            observed=observed,
        )
    score = (
        clamp01(dose_e_uGy_h / t.score_full_scale_uGy_h) if t.score_full_scale_uGy_h > 0 else 0.0
    )
    warnings = ("HIGH_RADIATION_RATE",) if dose_e_uGy_h >= t.warning_uGy_h else ()
    return FactorAssessment(
        factor_id=FACTOR_RADIATION,
        available=True,
        score=score,
        warnings=warnings,
        observed=observed,
    )
