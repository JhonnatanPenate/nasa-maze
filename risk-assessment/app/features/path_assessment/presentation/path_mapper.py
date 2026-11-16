from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.risk_level import RiskLevel
from app.features.path_assessment.domain.path_risk import (
    PathRisk,
    RiskSegment,
)
from app.features.path_assessment.presentation.path_schemas import (
    EvaluateResponse,
    RiskSegmentSchema,
)
from app.features.point_assessment.presentation.point_schemas import (
    FactorScoreSchema,
)


class PathMapper:
    """Domain -> DTO adapter for path risk results."""

    @staticmethod
    def _factor_scores(
        assessments: tuple[FactorAssessment, ...],
    ) -> dict[str, FactorScoreSchema]:
        return {
            a.factor_id: FactorScoreSchema(score=a.score, available=a.available)
            for a in assessments
        }

    @staticmethod
    def _segment(segment: RiskSegment) -> RiskSegmentSchema:
        # Aliased fields ("from"/"to") can't be kwargs; validate by alias.
        return RiskSegmentSchema.model_validate(
            {
                "from": {
                    "lat": segment.start.lat,
                    "lon": segment.start.lon,
                },
                "to": {"lat": segment.end.lat, "lon": segment.end.lon},
                "distance_m": segment.distance_m,
                "risk": segment.risk,
                "factor_scores": {
                    a.factor_id: {"score": a.score, "available": a.available}
                    for a in segment.factor_scores
                },
                "warnings": list(segment.warnings),
                "local_time_hour": segment.local_time_hour,
            }
        )

    @staticmethod
    def to_response(risk: PathRisk) -> EvaluateResponse:
        return EvaluateResponse(
            overall_risk=risk.overall_risk,
            risk_level=RiskLevel(risk.level),
            segments=[PathMapper._segment(s) for s in risk.segments],
            warnings_summary=list(risk.warnings_summary),
            sol=risk.sol,
            hora=risk.hora,
            total_distance_m=risk.total_distance_m,
            max_level=(RiskLevel(risk.max_level) if risk.max_level is not None else None),
            mean_score=risk.mean_score,
            p95_score=risk.p95_score,
            dominant_factor=risk.dominant_factor,
            total_duration_s=risk.total_duration_s,
            end_local_time_hours=risk.end_local_time_hours,
            confidence=risk.confidence,
            provenance=risk.provenance or None,
            data_quality_notes=list(risk.data_quality_notes),
            assumptions=list(risk.assumptions),
            restrictions=[dict(r) for r in risk.restrictions],
            hotspots=[dict(h) for h in risk.hotspots],
            blocking_segments=list(risk.blocking_segments),
        )
