"""SPEC risk-level boundaries (SPEC §4.1/§5)."""

import pytest
from app.core.domain.risk_level import RiskLevel, level_for_score


@pytest.mark.parametrize(
    "score,expected",
    [
        (None, RiskLevel.UNKNOWN),
        (0.0, RiskLevel.LOW),
        (0.2499, RiskLevel.LOW),
        (0.25, RiskLevel.MEDIUM),
        (0.4999, RiskLevel.MEDIUM),
        (0.5, RiskLevel.HIGH),
        (0.7499, RiskLevel.HIGH),
        (0.75, RiskLevel.CRITICAL),
        (1.0, RiskLevel.CRITICAL),
    ],
)
def test_level_boundaries(score: float | None, expected: RiskLevel) -> None:
    assert level_for_score(score) is expected
