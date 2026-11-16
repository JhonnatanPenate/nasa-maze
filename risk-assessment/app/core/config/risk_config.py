"""Loaders + pydantic validation for ``config/*.yaml`` (plan §5).

All loaders fail fast with a clear message when a file is missing or
invalid — composition calls them once at startup.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from app.core.domain.vehicle_profile import VehicleProfile


class _YamlModel(BaseModel):
    model_config = {"extra": "allow"}


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read config file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping")
    return raw


# --- risk_weights.yaml -------------------------------------------------


class RiskWeightsConfig(_YamlModel):
    version: int = 1
    model_version: str = "ms5-risk-v0.1"
    weights: dict[str, float] = Field(default_factory=dict)

    @field_validator("weights")
    @classmethod
    def _weights_valid(cls, value: dict[str, float]) -> dict[str, float]:
        for factor, weight in value.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"Weight for factor '{factor}' must be in [0, 1], got {weight}")
        return value


def load_weights(config_dir: str | Path) -> RiskWeightsConfig:
    path = Path(config_dir) / "risk_weights.yaml"
    return RiskWeightsConfig(**_load_yaml(path))


# --- risk_thresholds.yaml ----------------------------------------------


class _ThresholdBand(_YamlModel):
    """Per-factor thresholds; keys mirror config/risk_thresholds.yaml."""

    score_floor_deg: float | None = None
    score_ceil_deg: float | None = None
    score_floor_m: float | None = None
    score_ceil_m: float | None = None
    warning_deg: float | None = None
    warning_m: float | None = None
    block_deg: float | None = None
    dark_fraction_threshold: float | None = None
    proximity_warning_m: float | None = None
    band_min_K: float | None = None
    band_max_K: float | None = None
    warning_margin_K: float | None = None
    warning_uGy_h: float | None = None


class _LevelThresholds(_YamlModel):
    low_max: float = 0.25
    medium_max: float = 0.5
    high_max: float = 0.75


class RiskThresholdsConfig(_YamlModel):
    version: int = 1
    slope: _ThresholdBand = Field(default_factory=_ThresholdBand)
    roughness: _ThresholdBand = Field(default_factory=_ThresholdBand)
    dunes: _ThresholdBand = Field(default_factory=_ThresholdBand)
    temperature: _ThresholdBand = Field(default_factory=_ThresholdBand)
    radiation: _ThresholdBand = Field(default_factory=_ThresholdBand)
    levels: _LevelThresholds = Field(default_factory=_LevelThresholds)


def load_thresholds(config_dir: str | Path) -> RiskThresholdsConfig:
    path = Path(config_dir) / "risk_thresholds.yaml"
    return RiskThresholdsConfig(**_load_yaml(path))


# --- vehicle_profiles.yaml ----------------------------------------------


class VehicleProfilesConfig(_YamlModel):
    version: int = 1
    profiles: list[dict[str, Any]] = Field(default_factory=list)


def load_vehicle_profiles(config_dir: str | Path) -> tuple[VehicleProfile, ...]:
    """Parse ``vehicle_profiles.yaml`` into validated domain objects."""
    path = Path(config_dir) / "vehicle_profiles.yaml"
    raw = _load_yaml(path)
    config = VehicleProfilesConfig(**raw)
    profiles: list[VehicleProfile] = []
    for entry in config.profiles:
        try:
            profiles.append(VehicleProfile(**entry))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid vehicle profile entry in {path}: {exc}") from exc
    names = [p.name for p in profiles]
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate vehicle profile names in {path}: {names}")
    return tuple(profiles)
