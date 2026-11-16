from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.domain.risk_level import RiskLevel
from app.features.point_assessment.presentation.point_schemas import (
    FactorScoreSchema,
)


class PathPointSchema(BaseModel):
    """Polyline vertex. Ranges are unconstrained here: GeoPoint raises
    DomainValidationError -> 400, not FastAPI's 422 (MS4 convention)."""

    lat: float
    lon: float


class EvaluateRequest(BaseModel):
    """SPEC §3.1 request + additive plan fields (plan §7.1)."""

    body: str = "mars"
    path: list[PathPointSchema]
    factors: list[str] | None = None
    sol: int | None = None
    hora: int = 12
    # Additive (plan §7.1): sampling step, vehicle profile, speed override.
    sampling_step_m: float | None = None
    vehicle_profile: str | None = None
    speed_mps: float | None = None


class CoordinateSchema(BaseModel):
    lat: float
    lon: float


class RiskSegmentSchema(BaseModel):
    """SPEC §4.1 segment: ``from``/``to`` are the sampled interval ends."""

    model_config = ConfigDict(populate_by_name=True)

    start: CoordinateSchema = Field(alias="from")
    end: CoordinateSchema = Field(alias="to")
    distance_m: float
    risk: float | None
    factor_scores: dict[str, FactorScoreSchema]
    warnings: list[str]
    # Additive (plan §4.4): LMST hour bin at segment arrival.
    local_time_hour: int | None = None


class EvaluateResponse(BaseModel):
    """SPEC §4.1 evaluate response + additive plan fields (§7.2)."""

    overall_risk: float | None
    risk_level: RiskLevel
    segments: list[RiskSegmentSchema]
    warnings_summary: list[str]
    # Additive plan fields.
    sol: int | None = None
    hora: int | None = None
    total_distance_m: float | None = None
    max_level: RiskLevel | None = None
    mean_score: float | None = None
    p95_score: float | None = None
    dominant_factor: str | None = None
    total_duration_s: float | None = None
    end_local_time_hours: float | None = None
    confidence: str | None = None  # "high" | "medium" | "low" (plan §4.1)
    provenance: dict[str, Any] | None = None
    data_quality_notes: list[str] = []
    assumptions: list[str] = []
    restrictions: list[dict[str, Any]] = []
    hotspots: list[dict[str, Any]] = []
    blocking_segments: list[int] = []
