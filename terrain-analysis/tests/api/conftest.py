from collections.abc import Callable

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.composition.dependencies import (
    get_raster_datasource,
    get_settings,
)
from app.core.config.settings import Settings
from app.core.errors.error_handlers import register_exception_handlers
from app.core.ports.raster_datasource import RasterDatasource
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

ClientFactory = Callable[..., TestClient]


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
