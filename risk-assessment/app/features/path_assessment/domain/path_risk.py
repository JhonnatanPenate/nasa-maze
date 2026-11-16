"""Domain result of a path risk evaluation (SPEC §3.1/§4.1 + plan §7.2)."""

from dataclasses import dataclass, field
from typing import Any

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.geo_point import GeoPoint
from app.core.domain.risk_level import RiskLevel


@dataclass(frozen=True)
class RiskSegment:
    """Risk over one sampled interval ``[start, end]``.

    Serialized as ``from``/``to`` per the SPEC example."""

    start: GeoPoint
    end: GeoPoint
    distance_m: float
    risk: float | None
    factor_scores: tuple[FactorAssessment, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathRisk:
    overall_risk: float | None
    level: RiskLevel
    segments: tuple[RiskSegment, ...]
    warnings_summary: tuple[str, ...] = ()
    total_distance_m: float = 0.0
    sol: int | None = None
    hora: int | None = None
    vehicle_profile: str | None = None
    # Additive plan fields (plan §7.2); null/empty until scoring lands.
    max_level: RiskLevel | None = None
    mean_score: float | None = None
    p95_score: float | None = None
    dominant_factor: str | None = None
    total_duration_s: float | None = None
    end_local_time_hours: float | None = None
    confidence: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    data_quality_notes: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    restrictions: tuple[dict[str, Any], ...] = ()
    hotspots: tuple[dict[str, Any], ...] = ()
    blocking_segments: tuple[int, ...] = ()
