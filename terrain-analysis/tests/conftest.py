import numpy as np
import pytest

from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from tests.fixtures.make_test_dem import write_test_dem

TEST_NODATA = -32768.0
TEST_DEM_EXTENT = BoundingBox(
    min_lon=77.4, min_lat=18.4, max_lon=77.6, max_lat=18.6
)


def make_small_dem() -> tuple[np.ndarray, BoundingBox]:
    """Deterministic 21x21 DEM: plane elevation[rows, cols] = 500 + 2c - 3r
    with one nodata cell at (5, 5). Values are exact in float32."""
    rows, cols = np.indices((21, 21))
    elevation = 500.0 + 2.0 * cols - 3.0 * rows
    elevation[5, 5] = TEST_NODATA
    return elevation, TEST_DEM_EXTENT


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def small_dem() -> tuple[np.ndarray, BoundingBox]:
    return make_small_dem()


@pytest.fixture
def dem_window_mapper(settings: Settings) -> DemWindowMapper:
    return DemWindowMapper(settings.planet_radius_km * 1000.0)


@pytest.fixture
def synthetic_datasource(
    small_dem: tuple[np.ndarray, BoundingBox],
    dem_window_mapper: DemWindowMapper,
    settings: Settings,
) -> SyntheticDemDatasource:
    elevation, extent = small_dem
    return SyntheticDemDatasource(
        elevation,
        extent,
        dem_window_mapper,
        settings.max_window_cells,
        nodata=TEST_NODATA,
    )


@pytest.fixture(scope="session")
def geotiff_path(tmp_path_factory):
    elevation, extent = make_small_dem()
    path = tmp_path_factory.mktemp("dem") / "test_dem.tif"
    write_test_dem(path, elevation, extent, nodata=TEST_NODATA)
    return path


@pytest.fixture(scope="session")
def geotiff_datasource(geotiff_path) -> GeoTiffRasterDatasource:
    settings = Settings()
    mapper = DemWindowMapper(settings.planet_radius_km * 1000.0)
    return GeoTiffRasterDatasource(
        str(geotiff_path), mapper, settings.max_window_cells
    )


@pytest.fixture(params=["synthetic", "geotiff"])
def datasource(request, synthetic_datasource, geotiff_datasource):
    """Datasource swap proof: the same tests run against both
    RasterDatasource implementations."""
    if request.param == "synthetic":
        return synthetic_datasource
    return geotiff_datasource
