"""environment_columns.yaml loader tests."""

from pathlib import Path

import pytest
from app.ingest.config_loader import load_environment_columns

CONFIG = Path(__file__).resolve().parents[2] / "config" / "environment_columns.yaml"


def test_shipped_config_loads() -> None:
    config = load_environment_columns(CONFIG)
    assert config.version == 1
    # REMS key columns map to canonical sol/hora.
    rems_keys = {spec.canonical for spec in config.rems.key_columns.values()}
    assert {"sol", "hora"} <= rems_keys
    # RAD selects the dose-E channel.
    assert config.rad.selected_channel == "dose_e_uGy_h"
    rad_values = {spec.canonical for spec in config.rad.value_columns.values()}
    assert "dose_e_uGy_h" in rad_values
    assert "dose_b_uGy_h" in rad_values


def test_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot read"):
        load_environment_columns(tmp_path / "nope.yaml")


def test_missing_section_fails(tmp_path: Path) -> None:
    bad = tmp_path / "environment_columns.yaml"
    bad.write_text("version: 1\nrems: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_environment_columns(bad)


def test_column_without_canonical_fails(tmp_path: Path) -> None:
    bad = tmp_path / "environment_columns.yaml"
    bad.write_text(
        "version: 1\n"
        "rems:\n  source: a.xlsx\n  sheet: S\n"
        "  key_columns:\n    sol: {unit: sol}\n"
        "rad:\n  source: b.xlsx\n  sheet: S\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="canonical"):
        load_environment_columns(bad)
