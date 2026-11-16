"""YAML config loaders: shipped config parses; bad files fail fast."""

from pathlib import Path

import pytest
from app.core.config.risk_config import (
    load_thresholds,
    load_vehicle_profiles,
    load_weights,
)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_shipped_weights_match_spec_defaults() -> None:
    config = load_weights(CONFIG_DIR)
    assert config.weights == {
        "slope": 0.4,
        "dunes": 0.2,
        "roughness": 0.15,
        "temperature": 0.15,
        "radiation": 0.1,
    }
    assert config.model_version


def test_shipped_thresholds_load() -> None:
    config = load_thresholds(CONFIG_DIR)
    assert config.levels.low_max == 0.25
    assert config.levels.high_max == 0.75
    assert config.slope.score_floor_deg == 5.0


def test_shipped_vehicle_profiles() -> None:
    profiles = load_vehicle_profiles(CONFIG_DIR)
    names = {p.name for p in profiles}
    assert "baseline_mars_rover" in names
    baseline = next(p for p in profiles if p.name == "baseline_mars_rover")
    assert baseline.slope_block_deg == 25.0


def test_missing_file_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot read"):
        load_weights(tmp_path)


def test_invalid_yaml_fails_fast(tmp_path: Path) -> None:
    (tmp_path / "risk_weights.yaml").write_text("weights: [unclosed", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_weights(tmp_path)


def test_non_mapping_yaml_fails(tmp_path: Path) -> None:
    (tmp_path / "vehicle_profiles.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_vehicle_profiles(tmp_path)


def test_duplicate_profile_names_rejected(tmp_path: Path) -> None:
    entry = (
        "version: 1\nprofiles:\n"
        "  - {name: p, description: d, nominal_speed_m_h: 1, tilt_speed_factor: x,"
        " dune_speed_factor: 1, slope_block_deg: 1, tilt_block_deg: 1,"
        " tilt_margin_sigma: 1, thermal_min_K: 1, thermal_max_K: 1,"
        " dose_budget_uGy: null}\n"
        "  - {name: p, description: d, nominal_speed_m_h: 1, tilt_speed_factor: x,"
        " dune_speed_factor: 1, slope_block_deg: 1, tilt_block_deg: 1,"
        " tilt_margin_sigma: 1, thermal_min_K: 1, thermal_max_K: 1,"
        " dose_budget_uGy: null}\n"
    )
    (tmp_path / "vehicle_profiles.yaml").write_text(entry, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        load_vehicle_profiles(tmp_path)
