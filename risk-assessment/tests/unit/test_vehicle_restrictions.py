"""Vehicle profile motion + restrictions (Javi optimizer assumptions).

Restrictions are reported separately and must never alter the SPEC
weighted risk (plan §4.1/§4.3).
"""

import pytest
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.restriction import evaluate_restrictions
from app.core.domain.risk_aggregator import aggregate
from app.core.domain.soil_type import SoilType
from app.core.domain.tilt_model import TiltPrediction
from app.core.domain.vehicle_profile import (
    VehicleProfile,
    effective_speed_m_h,
    travel_hours,
)

PROFILE = VehicleProfile(
    name="baseline_mars_rover",
    description="test",
    nominal_speed_m_h=1000.0,
    tilt_speed_factor="max(0.1, 1 - tilt_deg/30)",
    dune_speed_factor=0.40,
    slope_block_deg=25.0,
    tilt_block_deg=20.0,
    tilt_margin_sigma=1.96,
    thermal_min_K=230.0,
    thermal_max_K=290.0,
    dose_budget_uGy=None,
)

WEIGHTS = {"slope": 0.4, "dunes": 0.2, "roughness": 0.15, "temperature": 0.15, "radiation": 0.1}


# --- effective speed --------------------------------------------------------


def test_effective_speed_nominal_without_tilt() -> None:
    assert effective_speed_m_h(PROFILE, tilt_deg=None, soil=None) == 1000.0
    assert effective_speed_m_h(PROFILE, tilt_deg=0.0, soil=None) == 1000.0


def test_effective_speed_tilt_penalty() -> None:
    # 1000 * max(0.1, 1 - 15/30) = 500
    assert effective_speed_m_h(PROFILE, tilt_deg=15.0, soil=None) == pytest.approx(500.0)
    # tilt >= 30 -> floor 0.1 -> 100 m/h
    assert effective_speed_m_h(PROFILE, tilt_deg=40.0, soil=None) == pytest.approx(100.0)


def test_effective_speed_dune_multiplier() -> None:
    # Javi: v *= (1 - FACTOR_DESLIZAMIENTO_ARENA) = 0.40 on arena_dunas.
    speed = effective_speed_m_h(PROFILE, tilt_deg=0.0, soil=SoilType.ARENA_DUNAS)
    assert speed == pytest.approx(400.0)
    # Non-dune soils keep the full speed.
    assert effective_speed_m_h(PROFILE, tilt_deg=0.0, soil=SoilType.REGOLITO_COMPACTO) == 1000.0


def test_travel_hours() -> None:
    assert travel_hours(1000.0, 1000.0) == pytest.approx(1.0)
    assert travel_hours(500.0, 250.0) == pytest.approx(2.0)
    with pytest.raises(ValueError, match="positive"):
        travel_hours(100.0, 0.0)


# --- restrictions ------------------------------------------------------------


def _tilt(tilt_deg: float, sigma: float = 1.0) -> TiltPrediction:
    return TiltPrediction(
        soil=None, model_label="global:test", tilt_deg=tilt_deg, sigma=sigma, r2=0.3
    )


def test_no_violations_no_restrictions() -> None:
    assert evaluate_restrictions(PROFILE, slope_deg=10.0, tilt=_tilt(5.0), temp_mean_K=250.0) == ()


def test_slope_block() -> None:
    result = evaluate_restrictions(PROFILE, slope_deg=25.0)
    assert len(result) == 1
    r = result[0]
    assert r.code == "SLOPE_BLOCK"
    assert r.blocking is True
    assert r.factor == "slope"
    assert r.value == 25.0 and r.limit == 25.0


def test_tilt_block_and_margin() -> None:
    # tilt 25 >= 20 -> TILT_BLOCK; margin 25+1.96*1=26.96 > 20 -> also margin.
    codes = {r.code for r in evaluate_restrictions(PROFILE, tilt=_tilt(25.0))}
    assert codes == {"TILT_BLOCK", "TILT_MARGIN_BLOCK"}
    # tilt 15, sigma 4 -> margin 15+7.84=22.84 > 20 but tilt < 20.
    codes = {r.code for r in evaluate_restrictions(PROFILE, tilt=_tilt(15.0, sigma=4.0))}
    assert codes == {"TILT_MARGIN_BLOCK"}
    # tilt 15, sigma 1 -> margin 16.96 <= 20 -> nothing.
    assert evaluate_restrictions(PROFILE, tilt=_tilt(15.0, sigma=1.0)) == ()


def test_thermal_out_of_band_is_advisory() -> None:
    result = evaluate_restrictions(PROFILE, temp_mean_K=200.0)
    assert len(result) == 1
    r = result[0]
    assert r.code == "THERMAL_OUT_OF_BAND"
    assert r.blocking is False  # Javi: cost penalty, not impassable
    assert r.factor == "temperature"


def test_missing_inputs_skip_rules() -> None:
    assert evaluate_restrictions(PROFILE) == ()


def test_restrictions_never_change_weighted_risk() -> None:
    """Plan §4.1: restrictions are reported separately — the SPEC weighted
    mean is identical whether or not a block fires."""
    assessments = (
        FactorAssessment(factor_id="slope", available=True, score=1.0),
        FactorAssessment(factor_id="temperature", available=True, score=0.5),
    )
    risk, _level = aggregate(assessments, WEIGHTS)
    restrictions = evaluate_restrictions(
        PROFILE, slope_deg=30.0, tilt=_tilt(25.0), temp_mean_K=200.0
    )
    assert restrictions  # blocks fired
    # Re-aggregating the same assessments is unaffected by restrictions.
    risk_again, _ = aggregate(assessments, WEIGHTS)
    assert risk == risk_again
    assert risk is not None and risk < 1.0  # not forced to critical/1.0
