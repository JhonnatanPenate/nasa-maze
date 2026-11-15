import math
from unittest.mock import Mock

import numpy as np
import pytest

from app.core.application.terrain_point_sample import TerrainPointSample
from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import (
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.core.ports.terrain_repository import TerrainRepository
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.slope_window import SlopeWindow
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
from tests.fakes.fake_slope_terrain_repository import (
    FakeSlopeTerrainRepository,
)

# Small DEM: extent lon 77.4..77.6, lat 18.4..18.6, 21x21 cells,
# elevation[r, c] = 500 + 2c - 3r, nodata cell (5, 5).
CELL_DEG = 0.2 / 21.0
NODATA_LAT = 18.6 - 5.5 * CELL_DEG
NODATA_LON = 77.4 + 5.5 * CELL_DEG

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


@pytest.fixture
def repository(
    synthetic_datasource: SyntheticDemDatasource,
) -> DemTerrainRepository:
    return DemTerrainRepository(synthetic_datasource)


@pytest.fixture
def sampler(repository: DemTerrainRepository) -> TerrainPointSampler:
    return TerrainPointSampler(repository, SlopeCalculator())


def _expected_plane_slope(window: DemWindow) -> float:
    # elevation[r, c] = 500 + 2c - 3r: true gradient is dz/dx = 2 m east,
    # dz/dy = -3 m north per cell.
    gradient = math.hypot(
        2.0 / window.cell_size_x_m, 3.0 / window.cell_size_y_m
    )
    return math.degrees(math.atan(gradient))


class TestSampleHappyPath:
    def test_returns_elevation_and_slope_at_cell(
        self,
        sampler: TerrainPointSampler,
        repository: DemTerrainRepository,
    ) -> None:
        point = GeoPoint(lat=18.5, lon=77.5)
        sample = sampler.sample(point)

        assert isinstance(sample, TerrainPointSample)
        assert sample.elevation_m == pytest.approx(490.0)
        window = repository.window_around(point, 1)
        assert sample.slope_deg == pytest.approx(
            _expected_plane_slope(window)
        )

    def test_single_window_read_per_sample(self) -> None:
        repository = Mock(spec=TerrainRepository)
        repository.provides_slope.return_value = False
        repository.window_around.return_value = DemWindow(
            elevation=np.full((3, 3), 100.0),
            cell_size_x_m=500.0,
            cell_size_y_m=500.0,
        )
        sampler = TerrainPointSampler(repository, SlopeCalculator())
        point = GeoPoint(lat=18.5, lon=77.5)

        sample = sampler.sample(point)

        repository.window_around.assert_called_once_with(point, 1)
        assert sample.elevation_m == pytest.approx(100.0)
        assert sample.slope_deg == pytest.approx(0.0)


class TestSampleEdge:
    def test_point_on_dem_edge_keeps_exact_plane_slope(
        self, sampler: TerrainPointSampler
    ) -> None:
        # Cell (0, 10): the window overhangs only the north edge, and the
        # mirror-extrapolation rule is exact for planar terrain.
        point = GeoPoint(lat=18.6, lon=77.5)
        sample = sampler.sample(point)

        assert sample.elevation_m == pytest.approx(520.0)
        assert sample.slope_deg > 0.0


class TestSampleFailures:
    def test_nodata_cell_raises_no_coverage(
        self, sampler: TerrainPointSampler
    ) -> None:
        with pytest.raises(NoCoverageError, match="No DEM coverage"):
            sampler.sample(GeoPoint(lat=NODATA_LAT, lon=NODATA_LON))

    def test_point_outside_extent_raises_no_coverage(
        self, sampler: TerrainPointSampler
    ) -> None:
        with pytest.raises(NoCoverageError, match="No DEM coverage"):
            sampler.sample(GeoPoint(lat=17.0, lon=77.5))

    def test_valid_centre_without_valid_neighbours_raises(self) -> None:
        # Only the centre cell holds data: the elevation is valid but the
        # slope is undefined (all 8 neighbours NaN).
        repository = Mock(spec=TerrainRepository)
        repository.provides_slope.return_value = False
        repository.window_around.return_value = DemWindow(
            elevation=np.array(
                [
                    [np.nan, np.nan, np.nan],
                    [np.nan, 100.0, np.nan],
                    [np.nan, np.nan, np.nan],
                ]
            ),
            cell_size_x_m=500.0,
            cell_size_y_m=500.0,
        )
        sampler = TerrainPointSampler(repository, SlopeCalculator())

        with pytest.raises(
            NoCoverageError,
            match="Slope undefined at .*no valid neighbouring cells",
        ):
            sampler.sample(GeoPoint(lat=18.5, lon=77.5))

    def test_datasource_failure_raises_upstream_error(self) -> None:
        sampler = TerrainPointSampler(
            DemTerrainRepository(FailingRasterDatasource()),
            SlopeCalculator(),
        )
        with pytest.raises(UpstreamDatasourceError):
            sampler.sample(GeoPoint(lat=18.5, lon=77.5))


class TestSampleGridMode:
    """Grid mode: slope comes pre-computed from the datasource, so the
    sampler reads a slope window and reports elevation_m as None; the
    SlopeCalculator must not be touched."""

    @pytest.fixture
    def slope_calculator(self) -> Mock:
        return Mock(spec=SlopeCalculator)

    @pytest.fixture
    def grid_sampler(self, slope_calculator: Mock) -> TerrainPointSampler:
        return TerrainPointSampler(
            FakeSlopeTerrainRepository(GRID_SLOPE, GRID_EXTENT),
            slope_calculator,
        )

    def test_returns_slope_from_window_and_null_elevation(
        self, grid_sampler: TerrainPointSampler, slope_calculator: Mock
    ) -> None:
        point = GeoPoint(lat=-8.5, lon=103.5)  # cell (3, 3) -> 19.0 deg

        sample = grid_sampler.sample(point)

        assert isinstance(sample, TerrainPointSample)
        assert sample.elevation_m is None
        assert sample.slope_deg == pytest.approx(19.0)
        slope_calculator.compute_at_center.assert_not_called()
        slope_calculator.compute.assert_not_called()

    def test_single_slope_window_read_with_radius_zero(self) -> None:
        repository = Mock(spec=TerrainRepository)
        repository.provides_slope.return_value = True
        repository.slope_window_around.return_value = SlopeWindow(
            slope_deg=np.array([[12.5]]),
            cell_size_x_m=90.0,
            cell_size_y_m=90.0,
        )
        sampler = TerrainPointSampler(repository, Mock(spec=SlopeCalculator))
        point = GeoPoint(lat=-8.5, lon=103.5)

        sample = sampler.sample(point)

        repository.slope_window_around.assert_called_once_with(point, 0)
        repository.window_around.assert_not_called()
        assert sample.elevation_m is None
        assert sample.slope_deg == pytest.approx(12.5)

    def test_nodata_cell_raises_no_coverage(
        self, grid_sampler: TerrainPointSampler
    ) -> None:
        with pytest.raises(
            NoCoverageError, match="lat=-7.5, lon=102.5"
        ):
            grid_sampler.sample(GeoPoint(lat=-7.5, lon=102.5))

    def test_point_outside_extent_raises_no_coverage(
        self, grid_sampler: TerrainPointSampler
    ) -> None:
        with pytest.raises(NoCoverageError):
            grid_sampler.sample(GeoPoint(lat=0.0, lon=103.5))
