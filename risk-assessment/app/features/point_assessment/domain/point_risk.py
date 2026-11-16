"""Domain result of a point risk assessment."""

from dataclasses import dataclass, field
from typing import Any

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.risk_level import RiskLevel


@dataclass(frozen=True)
class HourlyPointRisk:
    """Risk view for one LMST hour bin (used when ``hora`` is omitted and
    ``include_hourly=true`` — plan §7.1 additive behavior)."""

    hora: int
    risk: float | None
    level: RiskLevel
    factor_scores: tuple[FactorAssessment, ...]


@dataclass(frozen=True)
class PointRisk:
    lat: float
    lon: float
    risk: float | None
    level: RiskLevel
    factor_scores: tuple[FactorAssessment, ...]
    warnings: tuple[str, ...] = ()
    sol: int | None = None
    hora: int | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    by_hour: tuple[HourlyPointRisk, ...] | None = None
