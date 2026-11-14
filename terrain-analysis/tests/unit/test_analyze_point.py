import math
from unittest.mock import Mock

import numpy as np
import pytest

from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_class import TerrainClass
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.errors.exceptions import (
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.core.ports.terrain_repository import TerrainRepository
from app.features.point_analysis.application.analyze_point import AnalyzePoint
from app.features.point_analysis.domain.point_analysis import PointAnalysis
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Small DEM: extent lon 77.4..77.6, lat 18.4..18.6, 21x21 cells,
# elevation[r, c] = 500 + 2c - 3r, nodata cell (5, 5).
CELL_DEG = 0.2 / 21.0
NODATA_LAT = 18.6 - 5.5 * CELL_DEG
NODATA_LON = 77.4 + 5.5 * CELL_DEG


@pytest.fixture
def repository(
    synthetic_datasource: SyntheticDemDatasource,
) -> DemTerrainRepository:
    return DemTerrainRepository(synthetic_datasource)


@pytest.fixture
def use_case(repository: DemTerrainRepository) -> AnalyzePoint:
    return AnalyzePoint(
        TerrainPointSampler(repository, SlopeCalculator()),
        TerrainClassifier(),
    )


def expected_plane_slope(window: DemWindow) -> float:
    # elevation[r, c] = 500 + 2c - 3r, so the true surface gradient per
    # cell is dz/dx = 2 m east, dz/dy = -3 m north (row axis points south).
    gradient = math.hypot(
        2.0 / window.cell_size_x_m, 3.0 / window.cell_size_y_m
    )
    return math.degrees(math.atan(gradient))


class TestExecuteHappyPath:
    def test_returns_point_analysis_at_cell_centre(
        self,
        use_case: AnalyzePoint,
        repository: DemTerrainRepository,
    ) -> None:
        # (18.5, 77.5) is the centre of cell (10, 10): 500 + 20 - 30.
        point = GeoPoint(lat=18.5, lon=77.5)
        result = use_case.execute(point)

        assert isinstance(result, PointAnalysis)
        assert result.lat == 18.5
        assert result.lon == 77.5
        assert result.elevation_m == pytest.approx(490.0)
        window = repository.window_around(point, 1)
        assert result.slope_deg == pytest.approx(expected_plane_slope(window))
        assert result.terrain_class is TerrainClass.FLAT


class TestExecuteEdge:
    def test_point_on_dem_edge_keeps_exact_plane_slope(
        self,
        use_case: AnalyzePoint,
        repository: DemTerrainRepository,
    ) -> None:
        # Cell (0, 10): the window overhangs only the north edge, and the
        # mirror-extrapolation rule is exact for planar terrain.
        point = GeoPoint(lat=18.6, lon=77.5)
        result = use_case.execute(point)

        assert result.elevation_m == pytest.approx(520.0)
        window = repository.window_around(point, 1)
        assert result.slope_deg == pytest.approx(expected_plane_slope(window))
        assert result.terrain_class is TerrainClass.FLAT

    @pytest.mark.parametrize(
        "lat, lon, expected_elevation",
        [
            (18.6, 77.6, 540.0),  # max_lat/max_lon corner -> cell (0, 20)
            (18.4, 77.4, 440.0),  # min_lat/min_lon corner -> cell (20, 0)
        ],
    )
    def test_point_on_dem_corner_returns_data(
        self,
        use_case: AnalyzePoint,
        repository: DemTerrainRepository,
        lat: float,
        lon: float,
        expected_elevation: float,
    ) -> None:
        # At a corner both diagonal mirror cells are NaN, so the rule falls
        # back to the centre value for them; the slope is close to, but not
        # exactly, the true plane gradient.
        point = GeoPoint(lat=lat, lon=lon)
        result = use_case.execute(point)

        assert result.elevation_m == pytest.approx(expected_elevation)
        window = repository.window_around(point, 1)
        assert result.slope_deg == pytest.approx(
            expected_plane_slope(window), rel=0.05
        )
        assert result.terrain_class is TerrainClass.FLAT


class TestExecuteFailures:
    def test_nodata_cell_raises_no_coverage(
        self, use_case: AnalyzePoint
    ) -> None:
        with pytest.raises(NoCoverageError):
            use_case.execute(GeoPoint(lat=NODATA_LAT, lon=NODATA_LON))

    def test_point_outside_extent_raises_no_coverage(
        self, use_case: AnalyzePoint
    ) -> None:
        with pytest.raises(NoCoverageError):
            use_case.execute(GeoPoint(lat=17.0, lon=77.5))

    def test_datasource_failure_raises_upstream_error(self) -> None:
        use_case = AnalyzePoint(
            TerrainPointSampler(
                DemTerrainRepository(FailingRasterDatasource()),
                SlopeCalculator(),
            ),
            TerrainClassifier(),
        )
        with pytest.raises(UpstreamDatasourceError):
            use_case.execute(GeoPoint(lat=18.5, lon=77.5))


class TestRepositoryUsage:
    def test_single_window_read_with_radius_one(self) -> None:
        repository = Mock(spec=TerrainRepository)
        repository.window_around.return_value = DemWindow(
            elevation=np.full((3, 3), 100.0),
            cell_size_x_m=500.0,
            cell_size_y_m=500.0,
        )
        use_case = AnalyzePoint(
            TerrainPointSampler(repository, SlopeCalculator()),
            TerrainClassifier(),
        )
        point = GeoPoint(lat=18.5, lon=77.5)

        result = use_case.execute(point)

        repository.window_around.assert_called_once_with(point, 1)
        assert result.elevation_m == pytest.approx(100.0)
        assert result.slope_deg == pytest.approx(0.0)
        assert result.terrain_class is TerrainClass.FLAT
