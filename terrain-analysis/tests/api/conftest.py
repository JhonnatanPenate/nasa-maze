from collections.abc import Callable

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.composition.dependencies import get_raster_datasource
from app.core.errors.error_handlers import register_exception_handlers
from app.core.ports.raster_datasource import RasterDatasource
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

ClientFactory = Callable[[APIRouter], TestClient]


def _build_client(router: APIRouter, datasource: RasterDatasource) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_raster_datasource] = lambda: datasource
    return TestClient(app)


@pytest.fixture
def make_client(synthetic_datasource) -> ClientFactory:
    """TestClient over a single router, backed by the small deterministic DEM."""
    return lambda router: _build_client(router, synthetic_datasource)


@pytest.fixture
def make_failing_client() -> ClientFactory:
    """TestClient over a single router whose datasource always fails (502 path)."""
    return lambda router: _build_client(router, FailingRasterDatasource())
