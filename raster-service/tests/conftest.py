import pytest

from app.core.config.dataset_config import DatasetConfig
from app.core.config.settings import Settings
from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fixtures.make_test_raster import (
    TEST_BAND_NAMES,
    TEST_EXTENT,
    TEST_NODATA,
    test_bands,
    write_test_raster,
)

TEST_DATASET = "test"
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
