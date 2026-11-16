"""SPEC risk levels and score->level mapping (SPEC_MS5 §4.1/§5).

Boundaries are fixed by the SPEC: low < 0.25, medium 0.25-<0.5,
high 0.5-<0.75, critical >= 0.75, unknown when no factor is available.
"""

from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


LOW_MAX = 0.25
MEDIUM_MAX = 0.5
HIGH_MAX = 0.75


def level_for_score(score: float | None) -> RiskLevel:
    """Map a normalized score in [0, 1] to a SPEC risk level.

    ``None`` (no factor could be scored) maps to ``unknown`` — never a
    silent zero (SPEC §5)."""
    if score is None:
        return RiskLevel.UNKNOWN
    if score < LOW_MAX:
        return RiskLevel.LOW
    if score < MEDIUM_MAX:
        return RiskLevel.MEDIUM
    if score < HIGH_MAX:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL
