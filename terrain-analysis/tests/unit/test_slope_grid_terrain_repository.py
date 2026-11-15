from pathlib import Path

import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.core.ports.raster_datasource import RasterDatasource
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.repositories.slope_grid_terrain_repository import (
    SlopeGridTerrainRepository,
)
from tests.conftest import TEST_DEM_EXTENT, TEST_NODATA
from tests.fixtures.make_test_dem import write_test_grid

# Small slope grid: extent lon 77.4..77.6, lat 18.4..18.6, 21x21 cells,
# slope[r, c] = 5 + 0.5c + 0.25r degrees, nodata cell (5, 5).
# Band 2 of the GeoTIFF holds a different variable, so reading the wrong
# band fails the value assertions.
CELL_DEG = 0.2 / 21.0
NODATA_LAT = 18.6 - 5.5 * CELL_DEG
NODATA_LON = 77.4 + 5.5 * CELL_DEG
REAL_REJILLA = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "gale"
    / "processed"
    / "rejilla_ruta_90m.tif"
)


def make_slope_grid() -> tuple[np.ndarray, np.ndarray, BoundingBox]:
    rows, cols = np.indices((21, 21))
    slope = 5.0 + 0.5 * cols + 0.25 * rows
    other = 200.0 + cols + rows
    slope[5, 5] = TEST_NODATA
    other[5, 5] = TEST_NODATA
    return slope, other, TEST_DEM_EXTENT


@pytest.fixture
def slope_grid() -> tuple[np.ndarray, np.ndarray, BoundingBox]:
    return make_slope_grid()


@pytest.fixture(scope="module")
def slope_geotiff_path(tmp_path_factory):
    slope, other, extent = make_slope_grid()
    path = tmp_path_factory.mktemp("slope_grid") / "slope_grid.tif"
    write_test_grid(path, [slope, other], extent, nodata=TEST_NODATA)
    return path


@pytest.fixture(params=["synthetic", "geotiff"])
def slope_datasource(
    request, slope_grid, dem_window_mapper, settings, slope_geotiff_path
) -> RasterDatasource:
    """Datasource swap proof: identical expectations for a synthetic
    in-memory slope grid and a real multi-band GeoTIFF."""
    if request.param == "synthetic":
        slope, _, extent = slope_grid
        return SyntheticDemDatasource(
            slope,
            extent,
            dem_window_mapper,
            settings.max_window_cells,
            nodata=TEST_NODATA,
        )
    return GeoTiffRasterDatasource(
        str(slope_geotiff_path),
        dem_window_mapper,
        settings.max_window_cells,
        band=1,
    )


@pytest.fixture
def repository(slope_datasource: RasterDatasource) -> SlopeGridTerrainRepository:
    return SlopeGridTerrainRepository(slope_datasource)


class TestProvidesSlope:
    def test_provides_slope_true(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        assert repository.provides_slope() is True


class TestSlopeWindowAround:
    def test_returns_cell_slope(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        # Point (18.5, 77.5) is the centre of cell (10, 10): 5 + 5 + 2.5.
        window = repository.slope_window_around(GeoPoint(lat=18.5, lon=77.5), 0)
        assert window.slope_deg.shape == (1, 1)
        assert window.center_value() == 12.5
        assert window.cell_size_x_m > 0.0
        assert window.cell_size_y_m > 0.0

    @pytest.mark.parametrize(
        "lat, lon, expected",
        [
            (18.6, 77.6, 15.0),  # max corner -> cell (0, 20)
            (18.4, 77.4, 10.0),  # min corner -> cell (20, 0)
        ],
    )
    def test_point_on_grid_edge(
        self, repository: SlopeGridTerrainRepository, lat, lon, expected
    ) -> None:
        window = repository.slope_window_around(GeoPoint(lat=lat, lon=lon), 0)
        assert window.center_value() == expected

    def test_radius_window_values(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        window = repository.slope_window_around(GeoPoint(lat=18.5, lon=77.5), 1)
        assert window.slope_deg.shape == (3, 3)
        rows, cols = np.indices((3, 3))
        np.testing.assert_array_equal(
            window.slope_deg,
            5.0 + 0.5 * (cols + 9) + 0.25 * (rows + 9),
        )

    def test_nodata_cell_reads_as_nan(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        window = repository.slope_window_around(
            GeoPoint(lat=NODATA_LAT, lon=NODATA_LON), 0
        )
        assert np.isnan(window.center_value())


class TestSlopeWindowFor:
    def test_shape_and_values(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        window = repository.slope_window_for(
            BoundingBox(
                min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
            )
        )
        assert window.slope_deg.shape == (3, 3)
        rows, cols = np.indices((3, 3))
        np.testing.assert_array_equal(
            window.slope_deg,
            5.0 + 0.5 * (cols + 9) + 0.25 * (rows + 9),
        )

    def test_bbox_outside_extent_raises(
        self, repository: SlopeGridTerrainRepository
    ) -> None:
        with pytest.raises(NoCoverageError):
            repository.slope_window_for(
                BoundingBox(
                    min_lon=80.0, min_lat=18.0, max_lon=81.0, max_lat=19.0
                )
            )


class TestDemMethodsUnsupported:
    @pytest.mark.parametrize(
        "call",
        [
            lambda repo: repo.elevation_at(GeoPoint(lat=18.5, lon=77.5)),
            lambda repo: repo.window_around(GeoPoint(lat=18.5, lon=77.5), 0),
            lambda repo: repo.window_for(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49,
                    max_lon=77.51, max_lat=18.51,
                )
            ),
            lambda repo: repo.window_for_with_halo(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49,
                    max_lon=77.51, max_lat=18.51,
                ),
                1,
            ),
        ],
        ids=["elevation_at", "window_around", "window_for", "window_for_with_halo"],
    )
    def test_dem_methods_raise(
        self, repository: SlopeGridTerrainRepository, call
    ) -> None:
        with pytest.raises(NotImplementedError, match="elevation band"):
            call(repository)


class TestGeoTiffBandSelection:
    def test_band_two_reads_second_band(
        self, slope_geotiff_path, dem_window_mapper, settings
    ) -> None:
        ds = GeoTiffRasterDatasource(
            str(slope_geotiff_path),
            dem_window_mapper,
            settings.max_window_cells,
            band=2,
        )
        repository = SlopeGridTerrainRepository(ds)
        window = repository.slope_window_around(GeoPoint(lat=18.5, lon=77.5), 0)
        assert window.center_value() == 200.0 + 10.0 + 10.0

    @pytest.mark.parametrize("band", [0, 7])
    def test_band_out_of_range_raises(
        self, slope_geotiff_path, dem_window_mapper, settings, band
    ) -> None:
        ds = GeoTiffRasterDatasource(
            str(slope_geotiff_path),
            dem_window_mapper,
            settings.max_window_cells,
            band=band,
        )
        repository = SlopeGridTerrainRepository(ds)
        with pytest.raises(UpstreamDatasourceError):
            repository.slope_window_around(GeoPoint(lat=18.5, lon=77.5), 0)
        assert repository.is_available() is False

    def test_missing_file_upstream_error(
        self, tmp_path, dem_window_mapper, settings
    ) -> None:
        ds = GeoTiffRasterDatasource(
            str(tmp_path / "missing.tif"),
            dem_window_mapper,
            settings.max_window_cells,
            band=1,
        )
        repository = SlopeGridTerrainRepository(ds)
        with pytest.raises(UpstreamDatasourceError):
            repository.slope_window_for(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49,
                    max_lon=77.51, max_lat=18.51,
                )
            )
        assert repository.is_available() is False

    @pytest.mark.skipif(
        not REAL_REJILLA.exists(), reason="delivered rejilla grid not present"
    )
    def test_real_rejilla_file_pings(
        self, dem_window_mapper, settings
    ) -> None:
        ds = GeoTiffRasterDatasource(
            str(REAL_REJILLA),
            dem_window_mapper,
            settings.max_window_cells,
            band=settings.rejilla_slope_band,
        )
        assert ds.ping() is True
        repository = SlopeGridTerrainRepository(ds)
        assert repository.is_available() is True
        window = repository.slope_window_around(
            GeoPoint(lat=-4.66, lon=137.4), 0
        )
        assert np.isfinite(window.center_value())
