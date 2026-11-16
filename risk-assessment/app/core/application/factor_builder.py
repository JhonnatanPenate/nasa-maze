"""Shared factor scoring + availability logic for point and path assessment.

Wires the Phase 3 pure-domain scorers (``core/domain/*_risk.py``) into
``FactorAssessment`` results: every available factor returns a normalized
``score`` in [0, 1] plus its SPEC warning codes; unavailable factors keep
``score=None`` and never count as safe.

``ScoringThresholds`` bundles the per-factor threshold dataclasses; the
composition root builds it from ``config/risk_thresholds.yaml`` (the
application layer cannot import the pydantic config models).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.application.environment_context import EnvironmentalContext
from app.core.domain.dunes_risk import DunesThresholds, assess_dunes
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
from app.core.domain.radiation_risk import RadiationThresholds, assess_radiation
from app.core.domain.risk_level import RiskLevel
from app.core.domain.roughness_risk import RoughnessThresholds, assess_roughness
from app.core.domain.slope_risk import SlopeThresholds, assess_slope
from app.core.domain.temperature_risk import TemperatureThresholds, assess_temperature
from app.core.errors.exceptions import DomainValidationError

# Raster bands feeding each SPEC factor (SPEC §3.1 factor catalog).
ROUGHNESS_BAND = "rugosidad_m"
DUNES_BANDS = ("distancia_duna_m", "fraccion_oscura")

# Extra MS3 bands needed only by the soil classifier / tilt model
# (additive plan restrictions — not SPEC factors). ``pendiente_grados``
# comes from MS4 ``slope_deg`` instead (plan §4.2).
SOIL_EXTRA_BANDS = ("inercia_termica_tiu", "albedo")
# Full band set fetched for path evaluation: SPEC raster factors + soil/tilt.
PATH_BANDS = ("rugosidad_m", "fraccion_oscura", "inercia_termica_tiu", "albedo", "distancia_duna_m")


@dataclass(frozen=True)
class ScoringThresholds:
    """Per-factor scoring thresholds (domain dataclasses, plan §5)."""

    slope: SlopeThresholds
    roughness: RoughnessThresholds
    dunes: DunesThresholds
    temperature: TemperatureThresholds
    radiation: RadiationThresholds


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
    thresholds: ScoringThresholds,
) -> tuple[FactorAssessment, ...]:
    """Score every requested factor at one point/hour via the domain rules."""
    assessments: list[FactorAssessment] = []
    for factor_id in SPEC_FACTORS:
        if factor_id not in factors:
            continue
        if factor_id == FACTOR_SLOPE:
            assessments.append(assess_slope(slope_deg, thresholds.slope))
        elif factor_id == FACTOR_ROUGHNESS:
            assessments.append(
                assess_roughness(band_values.get(ROUGHNESS_BAND), thresholds.roughness)
            )
        elif factor_id == FACTOR_DUNES:
            assessments.append(
                assess_dunes(
                    band_values.get(DUNES_BANDS[0]),
                    band_values.get(DUNES_BANDS[1]),
                    thresholds.dunes,
                )
            )
        elif factor_id == FACTOR_TEMPERATURE:
            reading = context.temperature
            assessments.append(
                assess_temperature(
                    reading.ground_temp_mean_K if reading else None,
                    ground_temp_min_K=reading.ground_temp_min_K if reading else None,
                    ground_temp_max_K=reading.ground_temp_max_K if reading else None,
                    air_temp_mean_K=reading.air_temp_mean_K if reading else None,
                    thresholds=thresholds.temperature,
                )
            )
        elif factor_id == FACTOR_RADIATION:
            rad_reading = context.radiation
            assessments.append(
                assess_radiation(
                    rad_reading.dose_e_uGy_h if rad_reading else None,
                    dose_b_uGy_h=rad_reading.dose_b_uGy_h if rad_reading else None,
                    unit=rad_reading.unit if rad_reading else None,
                    provenance=rad_reading.provenance if rad_reading else None,
                    thresholds=thresholds.radiation,
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
    thresholds: ScoringThresholds,
) -> tuple[FactorAssessment, ...]:
    """Same scoring for one path sample (values come from the aligned
    MS3/MS4 sample lists instead of a point read)."""
    slope_deg = slope_sample.slope_deg if slope_sample else None
    band_values = {
        band: (sample.value if sample else None) for band, sample in band_samples.items()
    }
    return build_point_assessments(
        factors=factors,
        slope_deg=slope_deg,
        band_values=band_values,
        context=context,
        thresholds=thresholds,
    )


def provenance_for(context: EnvironmentalContext, model_version: str) -> dict[str, object]:
    return {
        "reference_sol": context.reference_sol,
        "rems_sol": context.rems_sol,
        "rad_sol": context.rad_sol,
        "scoring": model_version,
    }


# --- additive explanatory helpers (plan §4.5/§7.2) -----------------------


def merged_warnings(
    assessments_per_sample: Sequence[Sequence[FactorAssessment]],
) -> tuple[str, ...]:
    """Union of factor warnings across samples, first-seen order preserved."""
    seen: dict[str, None] = {}
    for assessments in assessments_per_sample:
        for assessment in assessments:
            for warning in assessment.warnings:
                seen.setdefault(warning)
    return tuple(seen)


def coverage_confidence(
    scored_cells: int,
    total_cells: int,
) -> str:
    """Plan §4.1 ``confidence ∈ {high, medium, low}`` from factor coverage.

    ``scored_cells`` counts assessments that are available AND scored;
    ``total_cells`` counts every assessed (sample x factor) cell. Placeholder
    heuristic pending calibration (documented in the phase report).
    """
    if total_cells <= 0:
        return "low"
    ratio = scored_cells / total_cells
    if ratio >= 0.9:
        return "high"
    if ratio >= 0.5:
        return "medium"
    return "low"


def scored_cell_counts(
    assessments_per_sample: Sequence[Sequence[FactorAssessment]],
) -> tuple[int, int]:
    """``(scored, total)`` cells across samples for ``coverage_confidence``."""
    total = 0
    scored = 0
    for assessments in assessments_per_sample:
        for assessment in assessments:
            total += 1
            if assessment.available and assessment.score is not None:
                scored += 1
    return scored, total


def coverage_notes(
    factor_ids: Sequence[str],
    assessments_per_sample: Sequence[Sequence[FactorAssessment]],
) -> tuple[str, ...]:
    """``data_quality_notes`` entries for factors with missing coverage."""
    notes: list[str] = []
    total = len(assessments_per_sample)
    for factor_id in factor_ids:
        missing = sum(
            1
            for assessments in assessments_per_sample
            if not any(
                a.factor_id == factor_id and a.available and a.score is not None
                for a in assessments
            )
        )
        if missing and total:
            notes.append(f"factor '{factor_id}' unavailable on {missing}/{total} samples")
    return tuple(notes)


def sol_fallback_notes(contexts: Sequence[EnvironmentalContext]) -> tuple[str, ...]:
    """Note when the nearest-sol fallback differs from the requested sol."""
    if not contexts:
        return ()
    first = contexts[0]
    notes: list[str] = []
    if first.rems_sol is not None and first.rems_sol != first.reference_sol:
        notes.append(
            f"nearest-sol fallback: rems_sol={first.rems_sol} "
            f"(requested {first.reference_sol})"
        )
    if first.rad_sol is not None and first.rad_sol != first.reference_sol:
        notes.append(
            f"nearest-sol fallback: rad_sol={first.rad_sol} "
            f"(requested {first.reference_sol})"
        )
    return tuple(notes)


def level_rank(level: RiskLevel) -> int:
    """Severity ordering for summary stats (``unknown`` sorts lowest)."""
    return {
        RiskLevel.UNKNOWN: 0,
        RiskLevel.LOW: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.HIGH: 3,
        RiskLevel.CRITICAL: 4,
    }[level]
