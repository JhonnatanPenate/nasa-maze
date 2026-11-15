from collections.abc import Callable

import numpy as np
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.composition.dependencies import (
    get_raster_datasource,
    get_settings,
    get_terrain_repository,
)
from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.errors.error_handlers import register_exception_handlers
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.terrain_repository import TerrainRepository
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
from tests.fakes.fake_slope_terrain_repository import (
    FakeSlopeTerrainRepository,
)

ClientFactory = Callable[..., TestClient]

# Slope grid: extent lon 100..105, lat -10..-5, 5x5 cells of 1 degree.
# Cell (r, c) centre is lat=-5.5-r, lon=100.5+c; (2, 2) is nodata.
GRID_SLOPE = np.array(
    [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [6.0, 7.0, 8.0, 9.0, 10.0],
        [11.0, 12.0, np.nan, 14.0, 15.0],
        [16.0, 17.0, 18.0, 19.0, 20.0],
        [21.0, 22.0, 23.0, 24.0, 25.0],
    ]
)
GRID_EXTENT = BoundingBox(
    min_lon=100.0, min_lat=-10.0, max_lon=105.0, max_lat=-5.0
)


def _build_client(
    router: APIRouter,
    datasource: RasterDatasource,
    settings: Settings | None = None,
) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_raster_datasource] = lambda: datasource
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def make_client(synthetic_datasource) -> ClientFactory:
    """TestClient over a single router, backed by the small deterministic
    DEM. Optional `datasource`/`settings` keyword arguments override the
    injected datasource or Settings."""

    def factory(
        router: APIRouter,
        datasource: RasterDatasource | None = None,
        settings: Settings | None = None,
    ) -> TestClient:
        return _build_client(
            router,
            datasource if datasource is not None else synthetic_datasource,
            settings,
        )

    return factory


@pytest.fixture
def make_failing_client() -> ClientFactory:
    """TestClient over a single router whose datasource always fails (502 path)."""
    return lambda router: _build_client(router, FailingRasterDatasource())


def _build_grid_client(
    router: APIRouter,
    repository: TerrainRepository,
    settings: Settings | None = None,
) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_terrain_repository] = lambda: repository
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def make_grid_client() -> ClientFactory:
    """TestClient over a single router whose repository serves
    pre-computed slope (grid mode): `provides_slope()` is True and
    `elevation_m` serializes as null. Optional `repository`/`settings`
    keyword arguments override the injected doubles."""

    def factory(
        router: APIRouter,
        repository: TerrainRepository | None = None,
        settings: Settings | None = None,
    ) -> TestClient:
        return _build_grid_client(
            router,
            repository
            if repository is not None
            else FakeSlopeTerrainRepository(GRID_SLOPE, GRID_EXTENT),
            settings,
        )

    return factory
