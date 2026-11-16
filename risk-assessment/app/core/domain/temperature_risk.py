"""``temperature`` factor scoring (SPEC §3.1/§5, plan §4.2).

Source: REMS hourly **ground-temperature mean** (``temp_suelo_K_media``,
Javi's ``temp_suelo`` variable) selected by the nearest REMS sol and the
LMST hour; REMS min/max are preserved as source summaries only.

Score uses Javi's hourly-mean excess formula
``max(0, band_min - T) + max(0, T - band_max)`` in kelvin, normalized by a
separately configurable full scale (``score_full_scale_K``, placeholder —
Javi defines the excess, not a [0, 1] scale; DECISIONS MS5-D16).

``EXTREME_COLD_ZONE`` (the SPEC's only suggested thermal code) fires when
the hourly mean leaves the operating band by more than
``warning_margin_K`` (placeholder interpretation, DECISIONS MS5-D16).
"""

from dataclasses import dataclass

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import FACTOR_TEMPERATURE
from app.core.domain.normalization import clamp01


@dataclass(frozen=True)
class TemperatureThresholds:
    band_min_K: float = 230.0  # Javi BANDA_TERMICA_OPERATIVA_K lower
    band_max_K: float = 290.0  # Javi BANDA_TERMICA_OPERATIVA_K upper
    warning_margin_K: float = 10.0  # placeholder (DECISIONS MS5-D16)
    score_full_scale_K: float = 60.0  # placeholder (DECISIONS MS5-D16)


def thermal_excess_K(temp_mean_K: float, band_min_K: float, band_max_K: float) -> float:
    """Javi's hourly-mean thermal excess in kelvin-hours per hour bin:
    ``max(0, min - T) + max(0, T - max)``. Zero inside the band."""
    return max(0.0, band_min_K - temp_mean_K) + max(0.0, temp_mean_K - band_max_K)


def assess_temperature(
    ground_temp_mean_K: float | None,
    *,
    ground_temp_min_K: float | None = None,
    ground_temp_max_K: float | None = None,
    air_temp_mean_K: float | None = None,
    thresholds: TemperatureThresholds | None = None,
) -> FactorAssessment:
    """Score REMS ground-temperature mean; ``None`` -> unavailable."""
    t = thresholds or TemperatureThresholds()
    observed: dict[str, float | str | None] = {
        "ground_temp_mean_K": ground_temp_mean_K,
        "ground_temp_min_K": ground_temp_min_K,
        "ground_temp_max_K": ground_temp_max_K,
        "air_temp_mean_K": air_temp_mean_K,
    }
    if ground_temp_mean_K is None:
        return FactorAssessment(
            factor_id=FACTOR_TEMPERATURE,
            available=False,
            observed=observed,
        )
    excess = thermal_excess_K(ground_temp_mean_K, t.band_min_K, t.band_max_K)
    score = clamp01(excess / t.score_full_scale_K) if t.score_full_scale_K > 0 else 0.0
    warnings: tuple[str, ...] = ()
    if (
        ground_temp_mean_K < t.band_min_K - t.warning_margin_K
        or ground_temp_mean_K > t.band_max_K + t.warning_margin_K
    ):
        warnings = ("EXTREME_COLD_ZONE",)
    return FactorAssessment(
        factor_id=FACTOR_TEMPERATURE,
        available=True,
        score=score,
        warnings=warnings,
        observed=observed,
    )
