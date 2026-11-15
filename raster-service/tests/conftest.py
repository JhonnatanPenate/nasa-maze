import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.composition.dependencies import get_repository, get_settings
from app.core.config.dataset_config import DatasetConfig
from app.core.config.settings import Settings
from app.core.errors.error_handlers import register_exception_handlers
from app.core.ports.raster_repository import RasterRepository
from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from app.main import create_app
from tests.fixtures.make_test_raster import (
    TEST_BAND_NAMES,
    TEST_EXTENT,
    TEST_NODATA,
    test_bands,
    write_test_raster,
)

TEST_DATASET = "test"
TEST_DATASET_PATH = "test/grid.tif"
TEST_BAND_UNITS = {
    "slope_deg": "deg",
    "roughness_m": "m",
    "dark_fraction": "fraction",
}


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def geotiff_path(tmp_path_factory):
    return write_test_raster(tmp_path_factory.mktemp("rasters") / "grid.tif")


@pytest.fixture
def memory_datasource() -> InMemoryRasterDatasource:
    return InMemoryRasterDatasource(
        test_bands(),
        TEST_EXTENT,
        band_descriptions=TEST_BAND_NAMES,
        nodata=TEST_NODATA,
    )


@pytest.fixture
def geotiff_datasource(geotiff_path) -> GeoTiffRasterDatasource:
    return GeoTiffRasterDatasource(geotiff_path)


@pytest.fixture(params=["memory", "geotiff"])
def datasource(request, memory_datasource, geotiff_datasource):
    if request.param == "memory":
        return memory_datasource
    return geotiff_datasource


@pytest.fixture
def dataset_config() -> DatasetConfig:
    return DatasetConfig(
        path="",
        band_units=dict(TEST_BAND_UNITS),
        colormaps={"slope_deg": "slope"},
        value_ranges={"slope_deg": (0.0, 35.0)},
    )


@pytest.fixture
def repository(datasource, dataset_config) -> RegistryRasterRepository:
    """Repository over the parametrized datasource — the swap proof: every
    test using this fixture runs once against the in-memory datasource and
    once against the generated GeoTIFF."""
    return RegistryRasterRepository(
        datasources={TEST_DATASET: datasource},
        configs={TEST_DATASET: dataset_config},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )


def mount_router(
    router: APIRouter,
    repository: RasterRepository,
    settings: Settings | None = None,
) -> TestClient:
    """Mount one router on a bare FastAPI app with the service error
    handlers. WP4/WP5 contract tests reuse this so they never touch
    app.main."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository
    if settings is not None:
        app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def api_dataset_config() -> DatasetConfig:
    return DatasetConfig(
        path=TEST_DATASET_PATH,
        kind="memory",
        band_units=dict(TEST_BAND_UNITS),
        colormaps={"slope_deg": "slope"},
        value_ranges={"slope_deg": (0.0, 35.0)},
    )


@pytest.fixture
def api_settings(api_dataset_config) -> Settings:
    return Settings(datasets={TEST_DATASET: api_dataset_config})


@pytest.fixture
def api_repository(
    memory_datasource, api_dataset_config
) -> RegistryRasterRepository:
    return RegistryRasterRepository(
        datasources={TEST_DATASET: memory_datasource},
        configs={TEST_DATASET: api_dataset_config},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )


@pytest.fixture
def make_client(api_repository, api_settings):
    """TestClient over create_app() with dependency_overrides in place.
    Optional `repository`/`settings` keyword arguments swap the injected
    doubles."""

    def factory(
        repository: RasterRepository | None = None,
        settings: Settings | None = None,
    ) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_repository] = (
            lambda: repository if repository is not None else api_repository
        )
        app.dependency_overrides[get_settings] = (
            lambda: settings if settings is not None else api_settings
        )
        return TestClient(app)

    return factory


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
