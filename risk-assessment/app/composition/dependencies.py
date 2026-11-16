"""Composition root: settings -> adapters -> use cases (plan §6).

The only module allowed to wire concrete infrastructure adapters to ports.
Modes: ``synthetic`` (deterministic fakes), ``http`` (MS3/MS4),
``unavailable`` (always-fail adapters -> factors report no coverage).

Process-wide singletons (settings, datasources, repos) are ``lru_cache``d
on hashable keys only — never on the ``Settings`` object itself.
"""

from functools import cache

import httpx
from fastapi import Depends

from app.core.application.environment_context import EnvironmentContextResolver
from app.core.config.risk_config import (
    RiskThresholdsConfig,
    RiskWeightsConfig,
    load_thresholds,
    load_weights,
)
from app.core.config.settings import Settings
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.factor_catalog import DEFAULT_WEIGHTS
from app.core.domain.path_sampler import PathSampler
from app.core.ports.environment_repository import EnvironmentRepository
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.core.ports.vehicle_profile_repository import VehicleProfileRepository
from app.features.area_assessment.application.assess_area import AssessArea
from app.features.path_assessment.application.evaluate_path import EvaluatePath
from app.features.point_assessment.application.assess_point import AssessPoint
from app.features.vehicle_profiles.application.list_vehicle_profiles import (
    ListVehicleProfiles,
)
from app.infrastructure.datasources.http_raster_source import HttpRasterSource
from app.infrastructure.datasources.http_terrain_source import HttpTerrainSource
from app.infrastructure.datasources.synthetic_raster_source import (
    SyntheticRasterSource,
)
from app.infrastructure.datasources.synthetic_terrain_source import (
    SyntheticTerrainSource,
)
from app.infrastructure.datasources.unavailable_sources import (
    UnavailableRasterSource,
    UnavailableTerrainSource,
)
from app.infrastructure.repositories.sqlite_environment_repository import (
    SqliteEnvironmentRepository,
)
from app.infrastructure.repositories.unavailable_environment_repository import (
    UnavailableEnvironmentRepository,
)
from app.infrastructure.repositories.yaml_vehicle_profile_repository import (
    YamlVehicleProfileRepository,
)


@cache
def get_settings() -> Settings:
    return Settings()


# --- shared domain services --------------------------------------------


def get_distance_calculator(
    settings: Settings = Depends(get_settings),
) -> DistanceCalculator:
    return DistanceCalculator(settings.planet_radius_m)


def get_path_sampler(
    distance_calculator: DistanceCalculator = Depends(get_distance_calculator),
) -> PathSampler:
    return PathSampler(distance_calculator)


# --- YAML config ---------------------------------------------------------


@cache
def _load_weights(config_dir: str) -> RiskWeightsConfig:
    return load_weights(config_dir)


def get_risk_weights(
    settings: Settings = Depends(get_settings),
) -> RiskWeightsConfig:
    return _load_weights(settings.config_dir)


@cache
def _load_thresholds(config_dir: str) -> RiskThresholdsConfig:
    return load_thresholds(config_dir)


def get_risk_thresholds(
    settings: Settings = Depends(get_settings),
) -> RiskThresholdsConfig:
    return _load_thresholds(settings.config_dir)


def _weights_dict(settings: Settings) -> dict[str, float]:
    config = _load_weights(settings.config_dir)
    return config.weights or dict(DEFAULT_WEIGHTS)


# --- upstream datasources -------------------------------------------------


def _build_terrain_source(settings: Settings) -> TerrainSource:
    mode = settings.datasource_mode
    if mode == "synthetic":
        return SyntheticTerrainSource(
            DistanceCalculator(settings.planet_radius_m),
            PathSampler(DistanceCalculator(settings.planet_radius_m)),
            settings.max_samples,
        )
    if mode == "http":
        client = httpx.Client(
            base_url=settings.terrain_base_url,
            timeout=settings.upstream_timeout_s,
        )
        return HttpTerrainSource(client, body=settings.body, retries=settings.upstream_retries)
    return UnavailableTerrainSource(f"datasource_mode={mode}")


def _build_raster_source(settings: Settings) -> RasterSource:
    mode = settings.datasource_mode
    if mode == "synthetic":
        calculator = DistanceCalculator(settings.planet_radius_m)
        return SyntheticRasterSource(calculator, PathSampler(calculator), settings.max_samples)
    if mode == "http":
        client = httpx.Client(
            base_url=settings.raster_base_url,
            timeout=settings.upstream_timeout_s,
        )
        return HttpRasterSource(client, dataset="rejilla", retries=settings.upstream_retries)
    return UnavailableRasterSource(f"datasource_mode={mode}")


@cache
def get_terrain_source() -> TerrainSource:
    """Process-wide terrain source; build failures degrade to unavailable
    (mirrors MS4 get_raster_datasource)."""
    settings = get_settings()
    try:
        return _build_terrain_source(settings)
    except Exception as exc:
        return UnavailableTerrainSource(f"build failed: {exc}")


@cache
def get_raster_source() -> RasterSource:
    settings = get_settings()
    try:
        return _build_raster_source(settings)
    except Exception as exc:
        return UnavailableRasterSource(f"build failed: {exc}")


# --- repositories ----------------------------------------------------------


@cache
def _environment_repository(path: str) -> EnvironmentRepository:
    return SqliteEnvironmentRepository(path)


def get_environment_repository(
    settings: Settings = Depends(get_settings),
) -> EnvironmentRepository:
    catalog = settings.effective_catalog_path
    if catalog is None:
        return UnavailableEnvironmentRepository()
    return _environment_repository(catalog)


@cache
def _vehicle_profile_repository(config_dir: str) -> VehicleProfileRepository:
    return YamlVehicleProfileRepository(config_dir)


def get_vehicle_profile_repository(
    settings: Settings = Depends(get_settings),
) -> VehicleProfileRepository:
    return _vehicle_profile_repository(settings.config_dir)


def get_env_context_resolver(
    environment: EnvironmentRepository = Depends(get_environment_repository),
    settings: Settings = Depends(get_settings),
) -> EnvironmentContextResolver:
    return EnvironmentContextResolver(environment, settings.default_sol)


# --- use cases -------------------------------------------------------------


def get_assess_point(
    terrain: TerrainSource = Depends(get_terrain_source),
    raster: RasterSource = Depends(get_raster_source),
    env_resolver: EnvironmentContextResolver = Depends(get_env_context_resolver),
    settings: Settings = Depends(get_settings),
) -> AssessPoint:
    return AssessPoint(
        terrain=terrain,
        raster=raster,
        env_resolver=env_resolver,
        weights=_weights_dict(settings),
    )


def get_evaluate_path(
    terrain: TerrainSource = Depends(get_terrain_source),
    raster: RasterSource = Depends(get_raster_source),
    env_resolver: EnvironmentContextResolver = Depends(get_env_context_resolver),
    vehicle_profiles: VehicleProfileRepository = Depends(get_vehicle_profile_repository),
    path_sampler: PathSampler = Depends(get_path_sampler),
    settings: Settings = Depends(get_settings),
) -> EvaluatePath:
    return EvaluatePath(
        terrain=terrain,
        raster=raster,
        env_resolver=env_resolver,
        vehicle_profiles=vehicle_profiles,
        path_sampler=path_sampler,
        weights=_weights_dict(settings),
        default_vehicle_profile=settings.default_vehicle_profile,
        max_path_points=settings.max_path_points,
        max_samples=settings.max_samples,
        default_sampling_step_m=settings.sampling_step_m,
    )


def list_vehicle_profiles(
    repository: VehicleProfileRepository = Depends(get_vehicle_profile_repository),
) -> ListVehicleProfiles:
    return ListVehicleProfiles(repository)


def get_assess_area(
    settings: Settings = Depends(get_settings),
) -> AssessArea:
    return AssessArea(settings.max_area_cells)
