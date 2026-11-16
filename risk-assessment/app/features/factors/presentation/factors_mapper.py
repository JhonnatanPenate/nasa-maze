from typing import ClassVar

from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import (
    FACTOR_DUNES,
    FACTOR_RADIATION,
    FACTOR_ROUGHNESS,
    FACTOR_SLOPE,
    FACTOR_TEMPERATURE,
    SPEC_FACTORS,
)
from app.features.factors.presentation.factors_schemas import (
    FactorInfoSchema,
    FactorsResponse,
)


class FactorsMapper:
    """Domain coverage state -> `GET /risk/factors` DTO."""

    _FACTOR_META: ClassVar[dict[str, tuple[str, str | None, list[str], str | None]]] = {
        FACTOR_SLOPE: (
            "Slope",
            "deg",
            ["MS4 /terrain/profile", "MS4 /terrain/point"],
            "Slope in degrees along the path/point.",
        ),
        FACTOR_ROUGHNESS: (
            "Surface roughness",
            "m",
            ["MS3 rejilla band rugosidad_m"],
            "RMS-ish surface roughness from the delivered grid.",
        ),
        FACTOR_DUNES: (
            "Dune proximity",
            None,
            ["MS3 rejilla bands distancia_duna_m, fraccion_oscura"],
            "Proximity to Bagnold dunes / dark sand fraction.",
        ),
        FACTOR_TEMPERATURE: (
            "Temperature",
            "K",
            ["REMS hourly climatology (rems_resumen_horario.xlsx)"],
            "Hourly air/ground temperature profile per sol + LMST hour.",
        ),
        FACTOR_RADIATION: (
            "Radiation",
            "uGy/h",
            ["RAD hourly climatology (rad_dosis_observaciones.xlsx, dose-E)"],
            "Hourly dose-E rate profile per sol + LMST hour.",
        ),
    }

    @staticmethod
    def to_response(
        assessments: dict[str, FactorAssessment],
        weights: dict[str, float],
        model_version: str,
        default_sol: int,
        rems_sols: tuple[int, ...],
        rad_sols: tuple[int, ...],
    ) -> FactorsResponse:
        factors = []
        for factor_id in SPEC_FACTORS:
            name, unit, sources, note = FactorsMapper._FACTOR_META[factor_id]
            assessment = assessments.get(factor_id)
            factors.append(
                FactorInfoSchema(
                    id=factor_id,
                    name=name,
                    unit=unit,
                    weight=weights.get(factor_id, 0.0),
                    available=bool(assessment and assessment.available),
                    sources=sources,
                    note=note,
                )
            )
        return FactorsResponse(
            factors=factors,
            weights=weights,
            model_version=model_version,
            default_sol=default_sol,
            environmental_sols={
                "rems": list(rems_sols),
                "rad": list(rad_sols),
            },
        )
