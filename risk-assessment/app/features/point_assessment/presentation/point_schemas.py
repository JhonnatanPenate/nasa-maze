from typing import Any

from pydantic import BaseModel

from app.core.domain.risk_level import RiskLevel


class FactorScoreSchema(BaseModel):
    """SPEC §4.1 ``factor_scores`` entry: normalized ``score`` in [0, 1]
    (null when the factor has no coverage) plus the ``available`` flag."""

    score: float | None
    available: bool


class HourlyRiskSchema(BaseModel):
    """Additive per-hour summary (plan §7.1, only with include_hourly)."""

    hora: int
    risk: float | None
    risk_level: RiskLevel
    factor_scores: dict[str, FactorScoreSchema]


class ProvenanceSchema(BaseModel):
    reference_sol: int
    rems_sol: int | None
    rad_sol: int | None
    scoring: str
    include_hourly: bool


class PointRiskResponse(BaseModel):
    """SPEC §4.2 point response + additive plan fields (§7.2)."""

    lat: float
    lon: float
    risk: float | None
    risk_level: RiskLevel
    factor_scores: dict[str, FactorScoreSchema]
    warnings: list[str]
    # Additive (plan §7.1/§7.2): echoed reference sol, resolved hour,
    # provenance and assumptions. None of these alter SPEC fields.
    sol: int | None = None
    hora: int | None = None
    confidence: str | None = None  # "high" | "medium" | "low" (plan §4.1)
    provenance: dict[str, Any] | None = None
    data_quality_notes: list[str] = []
    assumptions: list[str] = []
    by_hour: list[HourlyRiskSchema] | None = None
