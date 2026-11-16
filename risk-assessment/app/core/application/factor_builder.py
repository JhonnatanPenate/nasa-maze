"""Shared factor-availability logic for point and path assessment.

Phase 1 status: data plumbing is real (terrain/raster/environment reads
through the ports); per-factor *scoring* lands in Phase 3, so every
assessment carries ``score=None`` and aggregates to ``unknown``.
"""

from collections.abc import Mapping, Sequence

from app.core.application.environment_context import EnvironmentalContext
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import (
    FACTOR_DUNES,
    FACTOR_RADIATION,
    FACTOR_ROUGHNESS,
    FACTOR_SLOPE,
    FACTOR_TEMPERATURE,
    SPEC_FACTORS,
)
from app.core.domain.observations import BandSample, SlopeSample
from app.core.errors.exceptions import DomainValidationError

# Raster bands feeding each SPEC factor (SPEC §3.1 factor catalog).
ROUGHNESS_BAND = "rugosidad_m"
DUNES_BANDS = ("distancia_duna_m", "fraccion_oscura")


def validate_factor_selection(factors: Sequence[str] | None) -> tuple[str, ...]:
    """Subset of SPEC_FACTORS preserving catalog order; unknown ids -> 400."""
    if factors is None:
        return SPEC_FACTORS
    unknown = [f for f in factors if f not in SPEC_FACTORS]
    if unknown:
        raise DomainValidationError(
            f"Unknown risk factor(s) {unknown}; valid: {', '.join(SPEC_FACTORS)}"
        )
    requested = set(factors)
    return tuple(f for f in SPEC_FACTORS if f in requested)


def raster_factors_requested(factors: Sequence[str]) -> bool:
    return any(f in (FACTOR_ROUGHNESS, FACTOR_DUNES) for f in factors)


def terrain_requested(factors: Sequence[str]) -> bool:
    return FACTOR_SLOPE in factors


def build_point_assessments(
    *,
    factors: Sequence[str],
    slope_deg: float | None,
    band_values: Mapping[str, float | None],
    context: EnvironmentalContext,
) -> tuple[FactorAssessment, ...]:
    """Assemble per-factor availability + observed inputs at one point."""
    assessments: list[FactorAssessment] = []
    for factor_id in SPEC_FACTORS:
        if factor_id not in factors:
            continue
        if factor_id == FACTOR_SLOPE:
            assessments.append(
                FactorAssessment(
                    factor_id=factor_id,
                    available=slope_deg is not None,
                    observed={"slope_deg": slope_deg},
                )
            )
        elif factor_id == FACTOR_ROUGHNESS:
            value = band_values.get(ROUGHNESS_BAND)
            assessments.append(
                FactorAssessment(
                    factor_id=factor_id,
                    available=value is not None,
                    observed={ROUGHNESS_BAND: value},
                )
            )
        elif factor_id == FACTOR_DUNES:
            distance = band_values.get(DUNES_BANDS[0])
            dark = band_values.get(DUNES_BANDS[1])
            assessments.append(
                FactorAssessment(
                    factor_id=factor_id,
                    available=distance is not None or dark is not None,
                    observed={
                        DUNES_BANDS[0]: distance,
                        DUNES_BANDS[1]: dark,
                    },
                )
            )
        elif factor_id == FACTOR_TEMPERATURE:
            reading = context.temperature
            air = reading.air_temp_mean_K if reading else None
            assessments.append(
                FactorAssessment(
                    factor_id=factor_id,
                    available=air is not None,
                    observed={
                        "air_temp_mean_K": air,
                        "ground_temp_mean_K": (reading.ground_temp_mean_K if reading else None),
                        "rems_sol": context.rems_sol,
                    },
                )
            )
        elif factor_id == FACTOR_RADIATION:
            rad_reading = context.radiation
            dose = rad_reading.dose_e_uGy_h if rad_reading else None
            assessments.append(
                FactorAssessment(
                    factor_id=factor_id,
                    available=dose is not None,
                    observed={
                        "dose_e_uGy_h": dose,
                        "rad_sol": context.rad_sol,
                    },
                )
            )
        else:  # pragma: no cover - validate_factor_selection guards this
            raise DomainValidationError(f"Unhandled factor '{factor_id}'")
    return tuple(assessments)


def build_segment_assessments(
    *,
    factors: Sequence[str],
    slope_sample: SlopeSample | None,
    band_samples: Mapping[str, BandSample | None],
    context: EnvironmentalContext,
) -> tuple[FactorAssessment, ...]:
    """Same availability logic for one path sample (values come from the
    aligned MS3/MS4 sample lists instead of a point read)."""
    slope_deg = slope_sample.slope_deg if slope_sample else None
    band_values = {
        band: (sample.value if sample else None) for band, sample in band_samples.items()
    }
    return build_point_assessments(
        factors=factors,
        slope_deg=slope_deg,
        band_values=band_values,
        context=context,
    )


def provenance_for(context: EnvironmentalContext) -> dict[str, object]:
    return {
        "reference_sol": context.reference_sol,
        "rems_sol": context.rems_sol,
        "rad_sol": context.rad_sol,
        "scoring": "pending-phase-3",
    }
