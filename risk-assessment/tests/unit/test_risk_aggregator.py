"""SPEC weighted aggregation rules (SPEC §4.1/§5)."""

import pytest
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.risk_aggregator import aggregate
from app.core.domain.risk_level import RiskLevel

WEIGHTS = {
    "slope": 0.4,
    "dunes": 0.2,
    "roughness": 0.15,
    "temperature": 0.15,
    "radiation": 0.1,
}


def _a(factor: str, score: float | None, available: bool = True) -> FactorAssessment:
    return FactorAssessment(factor_id=factor, available=available, score=score)


def test_weighted_mean_over_available_scored_factors() -> None:
    # slope 0.8 * 0.4 + temperature 0.4 * 0.15, renormalized over 0.55.
    risk, level = aggregate([_a("slope", 0.8), _a("temperature", 0.4)], WEIGHTS)
    expected = (0.8 * 0.4 + 0.4 * 0.15) / 0.55  # ≈ 0.691 -> high
    assert risk == pytest.approx(expected)
    assert level is RiskLevel.HIGH


def test_unavailable_factors_excluded() -> None:
    risk, level = aggregate([_a("slope", 0.8), _a("dunes", 0.0, available=False)], WEIGHTS)
    assert risk == pytest.approx(0.8)
    assert level is RiskLevel.CRITICAL


def test_none_score_excluded_even_when_available() -> None:
    # Phase 1 state: available but unscored -> not weightable.
    risk, _level = aggregate([_a("slope", None), _a("radiation", 0.5)], WEIGHTS)
    assert risk == pytest.approx(0.5)


def test_no_scored_factors_returns_unknown_never_zero() -> None:
    risk, level = aggregate([_a("slope", None), _a("dunes", 0.9, available=False)], WEIGHTS)
    assert risk is None
    assert level is RiskLevel.UNKNOWN


def test_empty_assessments_returns_unknown() -> None:
    risk, level = aggregate([], WEIGHTS)
    assert risk is None
    assert level is RiskLevel.UNKNOWN


def test_score_out_of_range_rejected() -> None:
    with pytest.raises(ValueError, match="outside"):
        aggregate([_a("slope", 1.5)], WEIGHTS)


def test_missing_weight_treated_as_zero() -> None:
    risk, _ = aggregate([_a("unknown_factor", 0.5)], WEIGHTS)
    assert risk is None
