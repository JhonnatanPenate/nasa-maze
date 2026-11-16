from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.risk_level import RiskLevel
from app.features.point_assessment.domain.point_risk import (
    PointRisk,
)
from app.features.point_assessment.presentation.point_schemas import (
    FactorScoreSchema,
    HourlyRiskSchema,
    PointRiskResponse,
)


class PointMapper:
    """Domain -> DTO adapter for point risk results."""

    @staticmethod
    def _factor_scores(
        assessments: tuple[FactorAssessment, ...],
    ) -> dict[str, FactorScoreSchema]:
        return {
            a.factor_id: FactorScoreSchema(score=a.score, available=a.available)
            for a in assessments
        }

    @staticmethod
    def to_response(risk: PointRisk) -> PointRiskResponse:
        return PointRiskResponse(
            lat=risk.lat,
            lon=risk.lon,
            risk=risk.risk,
            risk_level=RiskLevel(risk.level),
            factor_scores=PointMapper._factor_scores(risk.factor_scores),
            warnings=list(risk.warnings),
            sol=risk.sol,
            hora=risk.hora,
            provenance=risk.provenance or None,
            by_hour=(
                [
                    HourlyRiskSchema(
                        hora=h.hora,
                        risk=h.risk,
                        risk_level=RiskLevel(h.level),
                        factor_scores=PointMapper._factor_scores(h.factor_scores),
                    )
                    for h in risk.by_hour
                ]
                if risk.by_hour is not None
                else None
            ),
        )
