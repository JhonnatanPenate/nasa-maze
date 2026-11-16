"""SPEC composite aggregation (SPEC_MS5 §4.1/§5).

Segment risk = weighted average over the factors that are *available and
scored*, renormalized by the sum of their weights. No scored factor ->
``(None, unknown)`` — never a silent zero.
"""

from collections.abc import Mapping, Sequence

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.risk_level import RiskLevel, level_for_score


def aggregate(
    assessments: Sequence[FactorAssessment],
    weights: Mapping[str, float],
) -> tuple[float | None, RiskLevel]:
    """Return ``(risk, level)`` for one segment/point.

    Only assessments with ``available=True`` and a non-``None`` score in
    [0, 1] contribute. The weighted mean divides by the sum of the
    contributing weights (SPEC "weighted average over available factors").
    """
    numerator = 0.0
    denominator = 0.0
    for assessment in assessments:
        if not assessment.available or assessment.score is None:
            continue
        score = assessment.score
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Factor {assessment.factor_id} score {score} outside [0, 1]")
        weight = float(weights.get(assessment.factor_id, 0.0))
        numerator += weight * score
        denominator += weight
    if denominator <= 0.0:
        return None, RiskLevel.UNKNOWN
    risk = numerator / denominator
    return min(1.0, max(0.0, risk)), level_for_score(risk)


def aggregate_path(
    segments: Sequence[tuple[float | None, float]],
) -> tuple[float | None, RiskLevel]:
    """SPEC §4.1 / plan §4.4: ``overall_risk`` = distance-weighted mean of
    segment risks. ``segments`` are ``(risk, distance_m)`` pairs; segments
    with ``risk=None`` or non-positive length do not contribute. All-empty
    -> ``(None, unknown)`` — never a silent zero."""
    numerator = 0.0
    denominator = 0.0
    for risk, distance_m in segments:
        if risk is None or distance_m <= 0.0:
            continue
        if not 0.0 <= risk <= 1.0:
            raise ValueError(f"Segment risk {risk} outside [0, 1]")
        numerator += risk * distance_m
        denominator += distance_m
    if denominator <= 0.0:
        return None, RiskLevel.UNKNOWN
    overall = numerator / denominator
    return min(1.0, max(0.0, overall)), level_for_score(overall)
