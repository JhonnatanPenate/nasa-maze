"""Shared fixtures: app + TestClient with a fake environmental catalog.

Default datasource mode is ``synthetic`` (deterministic MS3/MS4 fakes), so
API tests exercise the full plumbing without network. The environment
repository is overridden with ``FakeEnvironmentRepository`` populated for
the delivered sols {1360, 2140} (REMS) and {1360, 2140, 3290, 4710} (RAD).
"""

from collections.abc import Iterator

import pytest
from app.composition import dependencies
from app.core.ports.environment_repository import (
    RadiationReading,
    TemperatureReading,
)
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.fakes.fake_environment_repository import FakeEnvironmentRepository

# Inside the delivered rejilla extent (Phase 0 inventory).
GAP_POINT = {"lat": -4.62, "lon": 137.40}
GAP_PATH = [
    {"lat": -4.60, "lon": 137.44},
    {"lat": -4.65, "lon": 137.42},
]
# Outside the delivered grid -> synthetic sources raise NoCoverageError.
OFF_GRID_POINT = {"lat": 0.0, "lon": 0.0}


def full_environment() -> FakeEnvironmentRepository:
    rems = {
        (sol, hora): TemperatureReading(
            sol=sol,
            hora=hora,
            air_temp_mean_K=250.0,
            ground_temp_mean_K=255.0,
            ground_temp_min_K=240.0,
            ground_temp_max_K=265.0,
            pressure_mean_Pa=700.0,
            uv_abc_mean_W_m2=1.5,
        )
        for sol in (1360, 2140)
        for hora in range(24)
    }
    rad = {
        (sol, hora): RadiationReading(
            sol=sol,
            hora=hora,
            dose_e_uGy_h=12.5,
            dose_b_uGy_h=3.0,
            unit="uGy/h",
        )
        for sol in (1360, 2140, 3290, 4710)
        for hora in range(24)
    }
    return FakeEnvironmentRepository(rems=rems, rad=rad)


@pytest.fixture
def environment() -> FakeEnvironmentRepository:
    return full_environment()


@pytest.fixture
def app(environment: FakeEnvironmentRepository) -> FastAPI:
    application = create_app()
    application.dependency_overrides[dependencies.get_environment_repository] = lambda: environment
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def reset_singletons() -> None:
    """Clear every lru_cached composition singleton (mode-switch tests)."""
    for fn in (
        dependencies.get_settings,
        dependencies.get_terrain_source,
        dependencies.get_raster_source,
        dependencies._load_weights,
        dependencies._load_thresholds,
        dependencies._environment_repository,
        dependencies._vehicle_profile_repository,
    ):
        fn.cache_clear()
