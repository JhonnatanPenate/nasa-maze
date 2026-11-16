"""Phase 3 factor scoring: hand-computed values, clamping, monotonicity,
warning codes, and the nodata -> unavailable rule (plan §10)."""

import pytest
from app.core.domain.dunes_risk import assess_dunes
from app.core.domain.factor_catalog import (
    FACTOR_DUNES,
    FACTOR_RADIATION,
    FACTOR_ROUGHNESS,
    FACTOR_SLOPE,
    FACTOR_TEMPERATURE,
)
from app.core.domain.normalization import clamp01, linear_ramp
from app.core.domain.radiation_risk import RadiationThresholds, assess_radiation
from app.core.domain.roughness_risk import RoughnessThresholds, assess_roughness
from app.core.domain.slope_risk import SlopeThresholds, assess_slope
from app.core.domain.temperature_risk import (
    TemperatureThresholds,
    assess_temperature,
    thermal_excess_K,
)

# --- normalization helpers -------------------------------------------------


def test_linear_ramp_boundaries() -> None:
    assert linear_ramp(0.0, 5.0, 30.0) == 0.0
    assert linear_ramp(5.0, 5.0, 30.0) == 0.0
    assert linear_ramp(17.5, 5.0, 30.0) == pytest.approx(0.5)
    assert linear_ramp(30.0, 5.0, 30.0) == 1.0
    assert linear_ramp(99.0, 5.0, 30.0) == 1.0
    assert linear_ramp(-3.0, 5.0, 30.0) == 0.0


def test_linear_ramp_rejects_inverted_band() -> None:
    with pytest.raises(ValueError, match="floor < ceil"):
        linear_ramp(1.0, 5.0, 5.0)


def test_clamp01() -> None:
    assert clamp01(-0.5) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(1.5) == 1.0


# --- slope ---------------------------------------------------------------


def test_slope_spec_baseline() -> None:
    # SPEC §5 illustrative: 0 at <=5 deg, 1 at >=30 deg, linear between.
    assert assess_slope(3.0).score == 0.0
    assert assess_slope(5.0).score == 0.0
    assert assess_slope(17.5).score == pytest.approx(0.5)
    assert assess_slope(30.0).score == 1.0
    assert assess_slope(45.0).score == 1.0


def test_slope_monotonic() -> None:
    scores = [assess_slope(s).score for s in (5.0, 10.0, 15.0, 20.0, 25.0, 30.0)]
    assert scores == sorted(scores)
    assert len(set(scores)) == len(scores)


def test_slope_warning_javi_threshold() -> None:
    assert assess_slope(14.9).warnings == ()
    assert assess_slope(15.0).warnings == ("STEEP_SLOPE_15DEG",)
    assert assess_slope(27.6).warnings == ("STEEP_SLOPE_28DEG",)


def test_slope_unavailable_never_safe() -> None:
    result = assess_slope(None)
    assert result.available is False
    assert result.score is None
    assert result.factor_id == FACTOR_SLOPE


def test_slope_custom_thresholds() -> None:
    t = SlopeThresholds(score_floor_deg=10.0, score_ceil_deg=20.0, warning_deg=18.0)
    assert assess_slope(15.0, t).score == pytest.approx(0.5)
    assert assess_slope(15.0, t).warnings == ()
    assert assess_slope(19.0, t).warnings == ("STEEP_SLOPE_19DEG",)


# --- roughness ------------------------------------------------------------


def test_roughness_score_and_warning() -> None:
    # placeholder ramp 0.5 -> 3.0 m; warning at 1.5 m.
    assert assess_roughness(0.3).score == 0.0
    assert assess_roughness(1.75).score == pytest.approx(0.5)
    assert assess_roughness(1.75).warnings == ("HIGH_ROUGHNESS",)
    assert assess_roughness(1.4).warnings == ()
    assert assess_roughness(5.0).score == 1.0


def test_roughness_nodata_unavailable() -> None:
    result = assess_roughness(None)
    assert result.available is False
    assert result.score is None
    assert result.factor_id == FACTOR_ROUGHNESS


def test_roughness_custom_thresholds() -> None:
    t = RoughnessThresholds(score_floor_m=1.0, score_ceil_m=2.0, warning_m=1.8)
    assert assess_roughness(1.5, t).score == pytest.approx(0.5)
    assert assess_roughness(1.5, t).warnings == ()


# --- dunes ---------------------------------------------------------------


def test_dunes_on_dune_is_max_risk() -> None:
    result = assess_dunes(0.0, None)
    assert result.score == 1.0
    assert result.warnings == ("BAGNOLD_DUNES_NEARBY",)


def test_dunes_mid_values_hand_computed() -> None:
    # dist=50 -> 1 - 50/100 = 0.5; dark=0.2 -> 0.2/0.5 = 0.4; score = max = 0.5
    result = assess_dunes(50.0, 0.2)
    assert result.score == pytest.approx(0.5)
    assert result.warnings == ("BAGNOLD_DUNES_NEARBY",)  # 50 <= 100 m


def test_dunes_far_and_dark_low() -> None:
    result = assess_dunes(200.0, 0.1)
    assert result.score == pytest.approx(0.2)  # dark component only
    assert result.warnings == ()


def test_dunes_dark_fraction_alone() -> None:
    result = assess_dunes(None, 0.5)
    assert result.score == 1.0
    assert result.warnings == ("BAGNOLD_DUNES_NEARBY",)


def test_dunes_beyond_warning_distance_scores_zero_proximity() -> None:
    result = assess_dunes(500.0, 0.0)
    assert result.score == 0.0
    assert result.warnings == ()


def test_dunes_both_nodata_unavailable() -> None:
    result = assess_dunes(None, None)
    assert result.available is False
    assert result.score is None
    assert result.factor_id == FACTOR_DUNES


def test_dunes_partial_nodata_still_scores() -> None:
    # Only dark fraction available -> score from that component alone.
    result = assess_dunes(None, 0.25)
    assert result.available is True
    assert result.score == pytest.approx(0.5)


# --- temperature -----------------------------------------------------------


def test_thermal_excess_formula() -> None:
    # Javi: max(0, 230-T) + max(0, T-290), K per hour bin.
    assert thermal_excess_K(250.0, 230.0, 290.0) == 0.0
    assert thermal_excess_K(230.0, 230.0, 290.0) == 0.0
    assert thermal_excess_K(290.0, 230.0, 290.0) == 0.0
    assert thermal_excess_K(220.0, 230.0, 290.0) == 10.0
    assert thermal_excess_K(300.0, 230.0, 290.0) == 10.0


def test_temperature_inside_band_zero_score() -> None:
    result = assess_temperature(250.0)
    assert result.available is True
    assert result.score == 0.0
    assert result.warnings == ()


def test_temperature_excess_normalized() -> None:
    # T=200 -> excess 30 K -> 30/60 = 0.5 (placeholder full scale).
    result = assess_temperature(200.0)
    assert result.score == pytest.approx(0.5)
    assert result.warnings == ("EXTREME_COLD_ZONE",)


def test_temperature_hot_side() -> None:
    # T=350 -> excess 60 -> score 1.0; warning fires above band+margin.
    result = assess_temperature(350.0)
    assert result.score == 1.0
    assert result.warnings == ("EXTREME_COLD_ZONE",)


def test_temperature_warning_margin_boundary() -> None:
    # margin 10 K: warn only when T < 220 or T > 300.
    assert assess_temperature(220.0).warnings == ()
    assert assess_temperature(219.9).warnings == ("EXTREME_COLD_ZONE",)
    assert assess_temperature(300.0).warnings == ()
    assert assess_temperature(300.1).warnings == ("EXTREME_COLD_ZONE",)


def test_temperature_min_max_preserved_as_summaries() -> None:
    result = assess_temperature(
        250.0, ground_temp_min_K=240.0, ground_temp_max_K=265.0, air_temp_mean_K=255.0
    )
    assert result.observed is not None
    assert result.observed["ground_temp_min_K"] == 240.0
    assert result.observed["ground_temp_max_K"] == 265.0
    assert result.observed["air_temp_mean_K"] == 255.0


def test_temperature_nodata_unavailable() -> None:
    result = assess_temperature(None)
    assert result.available is False
    assert result.score is None
    assert result.factor_id == FACTOR_TEMPERATURE


def test_temperature_custom_thresholds() -> None:
    t = TemperatureThresholds(
        band_min_K=240.0, band_max_K=280.0, warning_margin_K=0.0, score_full_scale_K=20.0
    )
    # T=230 -> excess 10 -> score 0.5; margin 0 -> warns on any exit.
    result = assess_temperature(230.0, thresholds=t)
    assert result.score == pytest.approx(0.5)
    assert result.warnings == ("EXTREME_COLD_ZONE",)


# --- radiation --------------------------------------------------------------


def test_radiation_score_and_warning() -> None:
    # placeholder scale 30 uGy/h; warning at 20.
    assert assess_radiation(10.0).score == pytest.approx(10.0 / 30.0)
    assert assess_radiation(10.0).warnings == ()
    result = assess_radiation(20.0)
    assert result.score == pytest.approx(20.0 / 30.0)
    assert result.warnings == ("HIGH_RADIATION_RATE",)
    assert assess_radiation(45.0).score == 1.0  # clamped


def test_radiation_provenance_preserved() -> None:
    result = assess_radiation(
        10.66, dose_b_uGy_h=10.36, unit="uGy/hour", provenance="sol_mean_fallback"
    )
    assert result.observed is not None
    assert result.observed["provenance"] == "sol_mean_fallback"
    assert result.observed["dose_b_uGy_h"] == 10.36


def test_radiation_nodata_unavailable() -> None:
    result = assess_radiation(None)
    assert result.available is False
    assert result.score is None
    assert result.factor_id == FACTOR_RADIATION


def test_radiation_custom_thresholds() -> None:
    t = RadiationThresholds(warning_uGy_h=15.0, score_full_scale_uGy_h=15.0)
    result = assess_radiation(15.0, thresholds=t)
    assert result.score == 1.0
    assert result.warnings == ("HIGH_RADIATION_RATE",)


def test_factor_ids_match_spec_catalog() -> None:
    assert assess_slope(1.0).factor_id == FACTOR_SLOPE
    assert assess_roughness(1.0).factor_id == FACTOR_ROUGHNESS
    assert assess_dunes(1.0, 0.1).factor_id == FACTOR_DUNES
    assert assess_temperature(250.0).factor_id == FACTOR_TEMPERATURE
    assert assess_radiation(1.0).factor_id == FACTOR_RADIATION
