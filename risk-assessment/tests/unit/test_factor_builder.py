"""factor_builder wiring: Phase-3 scorers -> FactorAssessment + helpers."""

import pytest
from app.core.application.environment_context import EnvironmentalContext
from app.core.application.factor_builder import (
    ScoringThresholds,
    build_point_assessments,
    coverage_confidence,
    coverage_notes,
    level_rank,
    merged_warnings,
    provenance_for,
    scored_cell_counts,
    sol_fallback_notes,
    validate_factor_selection,
)
from app.core.domain.dunes_risk import DunesThresholds
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import SPEC_FACTORS
from app.core.domain.radiation_risk import RadiationThresholds
from app.core.domain.risk_level import RiskLevel
from app.core.domain.roughness_risk import RoughnessThresholds
from app.core.domain.slope_risk import SlopeThresholds
from app.core.domain.temperature_risk import TemperatureThresholds
from app.core.errors.exceptions import DomainValidationError
from app.core.ports.environment_repository import (
    RadiationReading,
    TemperatureReading,
)

THRESHOLDS = ScoringThresholds(
    slope=SlopeThresholds(),
    roughness=RoughnessThresholds(),
    dunes=DunesThresholds(),
    temperature=TemperatureThresholds(),
    radiation=RadiationThresholds(),
)


def _context(
    *,
    temperature: TemperatureReading | None = None,
    radiation: RadiationReading | None = None,
    rems_sol: int | None = 1360,
    rad_sol: int | None = 1360,
    reference_sol: int = 1360,
) -> EnvironmentalContext:
    return EnvironmentalContext(
        reference_sol=reference_sol,
        hora=9,
        rems_sol=rems_sol,
        rad_sol=rad_sol,
        temperature=temperature,
        radiation=radiation,
    )


def _temp(ground_mean: float | None = 255.0) -> TemperatureReading:
    return TemperatureReading(
        sol=1360,
        hora=9,
        air_temp_mean_K=250.0,
        ground_temp_mean_K=ground_mean,
        ground_temp_min_K=240.0,
        ground_temp_max_K=265.0,
        pressure_mean_Pa=700.0,
        uv_abc_mean_W_m2=1.5,
    )


def _rad(dose: float | None = 12.5) -> RadiationReading:
    return RadiationReading(
        sol=1360,
        hora=9,
        dose_e_uGy_h=dose,
        dose_b_uGy_h=3.0,
        unit="uGy/h",
        provenance="hourly_mean",
    )


def _assess(**kwargs) -> dict[str, FactorAssessment]:  # type: ignore[no-untyped-def]
    kwargs.setdefault("factors", SPEC_FACTORS)
    kwargs.setdefault("slope_deg", 10.0)
    kwargs.setdefault("band_values", {})
    kwargs.setdefault("context", _context(temperature=_temp(), radiation=_rad()))
    kwargs.setdefault("thresholds", THRESHOLDS)
    return {a.factor_id: a for a in build_point_assessments(**kwargs)}


def test_slope_score_and_warning() -> None:
    out = _assess(slope_deg=15.0)
    slope = out["slope"]
    assert slope.available is True
    assert slope.score == pytest.approx((15.0 - 5.0) / (30.0 - 5.0))
    assert slope.warnings == ("STEEP_SLOPE_15DEG",)


def test_slope_nodata_unavailable_never_safe() -> None:
    out = _assess(slope_deg=None)
    assert out["slope"].available is False
    assert out["slope"].score is None


def test_roughness_score_and_warning() -> None:
    out = _assess(band_values={"rugosidad_m": 1.5})
    assert out["roughness"].score == pytest.approx(0.4)
    assert out["roughness"].warnings == ("HIGH_ROUGHNESS",)


def test_dunes_mapped_cell_scores_one() -> None:
    out = _assess(band_values={"distancia_duna_m": 0.0, "fraccion_oscura": 0.1})
    assert out["dunes"].score == pytest.approx(1.0)
    assert out["dunes"].warnings == ("BAGNOLD_DUNES_NEARBY",)


def test_temperature_uses_ground_mean() -> None:
    out = _assess(context=_context(temperature=_temp(ground_mean=200.0), radiation=_rad()))
    temp = out["temperature"]
    # excess = 230-200 = 30 K -> 30/60 = 0.5; 200 < 230-10 -> warning.
    assert temp.score == pytest.approx(0.5)
    assert temp.warnings == ("EXTREME_COLD_ZONE",)


def test_temperature_in_band_scores_zero() -> None:
    out = _assess()
    assert out["temperature"].score == pytest.approx(0.0)
    assert out["temperature"].warnings == ()


def test_radiation_rate_scoring() -> None:
    out = _assess(context=_context(temperature=_temp(), radiation=_rad(25.0)))
    rad = out["radiation"]
    assert rad.score == pytest.approx(25.0 / 30.0)
    assert rad.warnings == ("HIGH_RADIATION_RATE",)


def test_missing_environment_is_unavailable() -> None:
    out = _assess(context=_context())
    assert out["temperature"].available is False
    assert out["temperature"].score is None
    assert out["radiation"].available is False
    assert out["radiation"].score is None


def test_factor_subset_and_catalog_order() -> None:
    out = _assess(factors=("radiation", "slope"))
    assert tuple(out) == ("slope", "radiation")  # SPEC catalog order


def test_unknown_factor_rejected() -> None:
    with pytest.raises(DomainValidationError):
        validate_factor_selection(("slope", "magical"))


def test_provenance_carries_model_version() -> None:
    prov = provenance_for(_context(), "ms5-risk-test")
    assert prov["scoring"] == "ms5-risk-test"
    assert prov["rems_sol"] == 1360


# --- additive explanatory helpers -----------------------------------------


def _fa(fid: str, score: float | None, available: bool = True, warn: str = "") -> FactorAssessment:
    return FactorAssessment(
        factor_id=fid,
        available=available,
        score=score,
        warnings=(warn,) if warn else (),
    )


def test_merged_warnings_dedup_first_seen() -> None:
    samples = [
        (_fa("slope", 0.5, warn="A"), _fa("dunes", 0.5, warn="B")),
        (_fa("slope", 0.6, warn="A"), _fa("dunes", 0.6, warn="C")),
    ]
    assert merged_warnings(samples) == ("A", "B", "C")


def test_scored_cell_counts() -> None:
    samples = [
        (_fa("slope", 0.5), _fa("dunes", None, available=False)),
        (_fa("slope", 0.6), _fa("dunes", 0.1)),
    ]
    assert scored_cell_counts(samples) == (3, 4)


@pytest.mark.parametrize(
    ("scored", "total", "expected"),
    [
        (10, 10, "high"),
        (9, 10, "high"),
        (8, 10, "medium"),
        (5, 10, "medium"),
        (4, 10, "low"),
        (0, 0, "low"),
    ],
)
def test_coverage_confidence_bands(scored: int, total: int, expected: str) -> None:
    assert coverage_confidence(scored, total) == expected


def test_coverage_notes_report_missing_factors() -> None:
    samples = [
        (_fa("slope", 0.5), _fa("radiation", None, available=False)),
        (_fa("slope", 0.6), _fa("radiation", None, available=False)),
    ]
    notes = coverage_notes(("slope", "radiation"), samples)
    assert notes == ("factor 'radiation' unavailable on 2/2 samples",)


def test_sol_fallback_notes() -> None:
    ctx = _context(reference_sol=5000, rems_sol=2140, rad_sol=4710)
    notes = sol_fallback_notes([ctx])
    assert notes == (
        "nearest-sol fallback: rems_sol=2140 (requested 5000)",
        "nearest-sol fallback: rad_sol=4710 (requested 5000)",
    )
    assert sol_fallback_notes([_context()]) == ()
    assert sol_fallback_notes([]) == ()


def test_level_rank_orders_severity() -> None:
    assert level_rank(RiskLevel.CRITICAL) > level_rank(RiskLevel.HIGH)
    assert level_rank(RiskLevel.UNKNOWN) < level_rank(RiskLevel.LOW)
