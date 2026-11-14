from unittest.mock import Mock

import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DomainValidationError,
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
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.conftest import TEST_NODATA
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Small DEM: extent lon 77.4..77.6, lat 18.4..18.6, 21x21 cells,
# elevation[r, c] = 500 + 2c - 3r, nodata cell (5, 5) = -32768.
CELL_DEG = 0.2 / 21.0
NODATA_LAT = 18.6 - 5.5 * CELL_DEG
NODATA_LON = 77.4 + 5.5 * CELL_DEG


@pytest.fixture
def repository(datasource: RasterDatasource) -> DemTerrainRepository:
    return DemTerrainRepository(datasource)


@pytest.fixture(params=["synthetic", "geotiff"])
def capped_datasource(
    request, small_dem, dem_window_mapper, geotiff_path
) -> RasterDatasource:
    """Both datasources with a 10-cell window cap for limit tests."""
    if request.param == "synthetic":
        elevation, extent = small_dem
        return SyntheticDemDatasource(
            elevation,
            extent,
            dem_window_mapper,
            max_window_cells=10,
            nodata=TEST_NODATA,
        )
    return GeoTiffRasterDatasource(
        str(geotiff_path), dem_window_mapper, max_window_cells=10
    )


class TestElevationAt:
    """Swap proof: identical expectations for synthetic and geotiff."""

    def test_returns_cell_elevation(
        self, repository: DemTerrainRepository
    ) -> None:
        # Point (18.5, 77.5) is the centre of cell (10, 10): 500 + 20 - 30.
        assert repository.elevation_at(GeoPoint(lat=18.5, lon=77.5)) == 490.0

    @pytest.mark.parametrize(
        "lat, lon, expected",
        [
            (18.6, 77.6, 540.0),  # max_lat/max_lon corner -> cell (0, 20)
            (18.4, 77.4, 440.0),  # min_lat/min_lon corner -> cell (20, 0)
        ],
    )
    def test_point_on_dem_boundary(
        self, repository: DemTerrainRepository, lat, lon, expected
    ) -> None:
        assert repository.elevation_at(GeoPoint(lat=lat, lon=lon)) == expected

    def test_nodata_cell_raises(
        self, repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(NoCoverageError):
            repository.elevation_at(GeoPoint(lat=NODATA_LAT, lon=NODATA_LON))

    def test_point_outside_extent_raises(
        self, repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(NoCoverageError):
            repository.elevation_at(GeoPoint(lat=17.0, lon=77.5))


class TestWindowFor:
    def test_shape_and_values(self, repository: DemTerrainRepository) -> None:
        # Cell centres inside: rows/cols 9..11.
        window = repository.window_for(
            BoundingBox(
                min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
            )
        )
        assert window.elevation.shape == (3, 3)
        np.testing.assert_array_equal(
            window.elevation,
            np.array(
                [
                    [491.0, 493.0, 495.0],
                    [488.0, 490.0, 492.0],
                    [485.0, 487.0, 489.0],
                ]
            ),
        )
        assert window.cell_size_x_m > 0.0
        assert window.cell_size_y_m > 0.0

    def test_bbox_outside_extent_raises(
        self, repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(NoCoverageError):
            repository.window_for(
                BoundingBox(
                    min_lon=80.0, min_lat=18.0, max_lon=81.0, max_lat=19.0
                )
            )


class TestWindowForWithHalo:
    """Swap proof for read_window_with_halo: identical expectations for
    the synthetic and geotiff datasources."""

    def test_halo_expands_window_with_real_cells(
        self, repository: DemTerrainRepository
    ) -> None:
        # Core cells rows/cols 9..11 plus a 1-cell halo -> 5x5 window.
        halo = repository.window_for_with_halo(
            BoundingBox(
                min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
            ),
            1,
        )
        assert halo.window.elevation.shape == (5, 5)
        assert halo.core_rows == slice(1, 4)
        assert halo.core_cols == slice(1, 4)
        rows, cols = np.indices((5, 5))
        np.testing.assert_array_equal(
            halo.window.elevation, 500.0 + 2.0 * (cols + 8) - 3.0 * (rows + 8)
        )

    def test_core_matches_plain_read(self, repository: DemTerrainRepository) -> None:
        bbox = BoundingBox(
            min_lon=77.35, min_lat=18.45, max_lon=77.45, max_lat=18.55
        )
        halo = repository.window_for_with_halo(bbox, 2)
        plain = repository.window_for(bbox)
        np.testing.assert_array_equal(halo.core().elevation, plain.elevation)
        assert halo.core().cell_size_x_m == pytest.approx(plain.cell_size_x_m)
        assert halo.core().cell_size_y_m == pytest.approx(plain.cell_size_y_m)

    def test_halo_clipped_at_dem_edge(
        self, repository: DemTerrainRepository
    ) -> None:
        # The bbox core touches the west edge (col 0): the halo can only
        # grow north/south/east, so the core touches the window's west edge.
        halo = repository.window_for_with_halo(
            BoundingBox(
                min_lon=77.35, min_lat=18.45, max_lon=77.45, max_lat=18.55
            ),
            1,
        )
        # Core: rows 5..15 (11 rows), cols 0..4 (5 cols). Halo adds 1 row
        # each side and 1 col on the east only.
        assert halo.window.elevation.shape == (13, 6)
        assert halo.core_rows == slice(1, 12)
        assert halo.core_cols == slice(0, 5)

    def test_zero_halo_equals_read_window(
        self, repository: DemTerrainRepository
    ) -> None:
        bbox = BoundingBox(
            min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
        )
        halo = repository.window_for_with_halo(bbox, 0)
        assert halo.core_rows == slice(0, 3)
        assert halo.core_cols == slice(0, 3)
        np.testing.assert_array_equal(
            halo.window.elevation, repository.window_for(bbox).elevation
        )

    def test_core_matches_plain_read_at_north_edge(
        self, repository: DemTerrainRepository
    ) -> None:
        """Asymmetric clipping: the bbox core touches the north DEM edge
        (row 0), so the halo grows south-only. core() must still match a
        plain read exactly — including cell_size_x_m, which is computed
        from the core rows' mean latitude, not the haloed span's."""
        bbox = BoundingBox(
            min_lon=77.45, min_lat=18.55, max_lon=77.55, max_lat=18.65
        )
        halo = repository.window_for_with_halo(bbox, 1)
        plain = repository.window_for(bbox)
        assert halo.core_rows.start == 0
        np.testing.assert_array_equal(halo.core().elevation, plain.elevation)
        assert halo.core().cell_size_x_m == plain.cell_size_x_m
        assert halo.core().cell_size_y_m == plain.cell_size_y_m

    def test_max_window_cells_applies_to_core(
        self, capped_datasource: RasterDatasource
    ) -> None:
        # Cap is 10 core cells; a 2x2 core + halo (4x4 = 16 cells read)
        # must still succeed because the cap counts core cells only.
        repository = DemTerrainRepository(capped_datasource)
        halo = repository.window_for_with_halo(
            BoundingBox(
                min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
            ),
            1,
        )
        # 3x3 core (9 cells <= 10) with halo -> 5x5 read.
        assert halo.window.elevation.shape == (5, 5)


class TestWindowAround:
    def test_shape_and_values(self, repository: DemTerrainRepository) -> None:
        window = repository.window_around(GeoPoint(lat=18.5, lon=77.5), 2)
        assert window.elevation.shape == (5, 5)
        rows, cols = np.indices((5, 5))
        np.testing.assert_array_equal(
            window.elevation, 500.0 + 2.0 * (cols + 8) - 3.0 * (rows + 8)
        )

    def test_nw_corner_padding_and_values(
        self, repository: DemTerrainRepository
    ) -> None:
        # Cell (0, 0) centre: radius-2 window overhangs the north and west
        # edges, so rows 0-1 and cols 0-1 of the output are NaN.
        point = GeoPoint(lat=18.6 - 0.5 * CELL_DEG, lon=77.4 + 0.5 * CELL_DEG)
        window = repository.window_around(point, 2)
        assert window.elevation.shape == (5, 5)
        assert np.isnan(window.elevation[:2, :]).all()
        assert np.isnan(window.elevation[:, :2]).all()
        np.testing.assert_array_equal(
            window.elevation[2:5, 2:5],
            np.array(
                [
                    [500.0, 502.0, 504.0],
                    [497.0, 499.0, 501.0],
                    [494.0, 496.0, 498.0],
                ]
            ),
        )

    def test_se_corner_padding_and_values(
        self, repository: DemTerrainRepository
    ) -> None:
        # Cell (20, 20) centre: the window overhangs the south and east
        # edges, so rows 3-4 and cols 3-4 of the output are NaN.
        point = GeoPoint(
            lat=18.6 - 20.5 * CELL_DEG, lon=77.4 + 20.5 * CELL_DEG
        )
        window = repository.window_around(point, 2)
        assert window.elevation.shape == (5, 5)
        assert np.isnan(window.elevation[3:, :]).all()
        assert np.isnan(window.elevation[:, 3:]).all()
        np.testing.assert_array_equal(
            window.elevation[0:3, 0:3],
            np.array(
                [
                    [482.0, 484.0, 486.0],
                    [479.0, 481.0, 483.0],
                    [476.0, 478.0, 480.0],
                ]
            ),
        )

    def test_is_available_true(
        self, repository: DemTerrainRepository
    ) -> None:
        assert repository.is_available() is True


class TestLimits:
    def test_max_window_cells_exceeded(
        self, capped_datasource: RasterDatasource
    ) -> None:
        repository = DemTerrainRepository(capped_datasource)
        with pytest.raises(DomainValidationError):
            # Full extent holds 21x21 = 441 cells > 10.
            repository.window_for(
                BoundingBox(
                    min_lon=77.4, min_lat=18.4, max_lon=77.6, max_lat=18.6
                )
            )

    def test_window_around_radius_cap(
        self, capped_datasource: RasterDatasource
    ) -> None:
        repository = DemTerrainRepository(capped_datasource)
        with pytest.raises(DomainValidationError):
            # radius 3 -> 7x7 = 49 cells > 10.
            repository.window_around(GeoPoint(lat=18.5, lon=77.5), 3)


class TestFailingDatasource:
    @pytest.fixture
    def failing_repository(self) -> DemTerrainRepository:
        return DemTerrainRepository(FailingRasterDatasource())

    def test_elevation_at_wraps_failure(
        self, failing_repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(UpstreamDatasourceError):
            failing_repository.elevation_at(GeoPoint(lat=18.5, lon=77.5))

    def test_window_for_wraps_failure(
        self, failing_repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(UpstreamDatasourceError):
            failing_repository.window_for(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
                )
            )

    def test_window_around_wraps_failure(
        self, failing_repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(UpstreamDatasourceError):
            failing_repository.window_around(GeoPoint(lat=18.5, lon=77.5), 1)

    def test_window_for_with_halo_wraps_failure(
        self, failing_repository: DemTerrainRepository
    ) -> None:
        with pytest.raises(UpstreamDatasourceError):
            failing_repository.window_for_with_halo(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
                ),
                1,
            )

    def test_is_available_false(
        self, failing_repository: DemTerrainRepository
    ) -> None:
        assert failing_repository.is_available() is False


class TestDomainErrorPassthrough:
    def test_domain_error_not_wrapped(self) -> None:
        error = NoCoverageError("no data here")
        datasource = Mock(spec=RasterDatasource)
        datasource.read_window_with_halo.side_effect = error
        repository = DemTerrainRepository(datasource)
        with pytest.raises(NoCoverageError) as excinfo:
            repository.window_for(
                BoundingBox(
                    min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
                )
            )
        assert excinfo.value is error
