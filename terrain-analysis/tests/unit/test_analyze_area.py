import math

import numpy as np
import pytest

from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.features.area_analysis.application.analyze_area import AnalyzeArea
from app.features.area_analysis.domain.area_stats import AreaStats
from app.features.area_analysis.domain.value_stats import ValueStats
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.conftest import TEST_DEM_EXTENT, TEST_NODATA
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

STEEP_MIN_DEG = Settings().slope_moderate_max_deg


def _bbox(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> BoundingBox:
    return BoundingBox(
        min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
    )


def _full_plane_slope_deg(window) -> float:
    # Plane elevation = 500 + 2c - 3r: gradient magnitude per cell is
    # hypot(2/cell_x, 3/cell_y); interior cells keep it exactly.
    return math.degrees(
        math.atan(
            math.hypot(
                2.0 / window.cell_size_x_m, 3.0 / window.cell_size_y_m
            )
        )
    )


@pytest.fixture
def repository(synthetic_datasource) -> DemTerrainRepository:
    return DemTerrainRepository(synthetic_datasource)


@pytest.fixture
def use_case(repository) -> AnalyzeArea:
    return AnalyzeArea(repository, SlopeCalculator(), STEEP_MIN_DEG)


class TestHappyPath:
    def test_small_bbox_stats(
        self, use_case: AnalyzeArea, repository: DemTerrainRepository
    ) -> None:
        # Cell centres inside: rows/cols 9..11 -> 3x3 window, no nodata.
        bbox = _bbox(77.49, 18.49, 77.51, 18.51)
        stats = use_case.execute(bbox)

        assert isinstance(stats, AreaStats)
        assert isinstance(stats.elevation_m, ValueStats)
        assert stats.elevation_m.min == pytest.approx(485.0)
        assert stats.elevation_m.max == pytest.approx(495.0)
        assert stats.elevation_m.mean == pytest.approx(490.0)

        window = repository.window_for(bbox)
        slopes = SlopeCalculator().compute(window)
        assert stats.slope_deg.min == pytest.approx(float(np.nanmin(slopes)))
        assert stats.slope_deg.max == pytest.approx(float(np.nanmax(slopes)))
        assert stats.slope_deg.mean == pytest.approx(float(np.nanmean(slopes)))
        # Near-constant slope on a plane: interior cells hit the exact
        # gradient, only window corners deviate slightly.
        assert stats.slope_deg.max == pytest.approx(
            _full_plane_slope_deg(window)
        )
        assert 0.0 <= stats.slope_deg.min <= stats.slope_deg.max
        assert stats.steep_fraction == 0.0


class TestEdgeCases:
    def test_bbox_partially_outside_extent_is_clipped(
        self, use_case: AnalyzeArea
    ) -> None:
        # min_lon 77.35 lies west of the DEM edge: clipped to cols 0..4,
        # rows 5..15 (centres within lat 18.45..18.55).
        stats = use_case.execute(_bbox(77.35, 18.45, 77.45, 18.55))

        rows, cols = np.indices((21, 21))
        expected = 500.0 + 2.0 * cols - 3.0 * rows
        clipped = expected[5:16, 0:5]
        assert stats.elevation_m.min == pytest.approx(float(np.min(clipped)))
        assert stats.elevation_m.max == pytest.approx(float(np.max(clipped)))
        assert stats.elevation_m.mean == pytest.approx(float(np.mean(clipped)))

    def test_nodata_cell_excluded_from_stats(
        self, use_case: AnalyzeArea
    ) -> None:
        # 3x3 window centred on the nodata cell (5, 5): stats cover the 8
        # valid cells only.
        stats = use_case.execute(_bbox(77.44, 18.53, 77.47, 18.56))
        assert stats.elevation_m.min == pytest.approx(490.0)
        assert stats.elevation_m.max == pytest.approx(500.0)
        assert stats.elevation_m.mean == pytest.approx(495.0)

    def test_steep_dem_gives_steep_fraction_one(
        self, dem_window_mapper: DemWindowMapper, settings: Settings
    ) -> None:
        # ~62 deg east gradient: every valid slope cell is >= steep_min_deg.
        _, cols = np.indices((21, 21))
        elevation = 1000.0 * cols
        datasource = SyntheticDemDatasource(
            elevation,
            TEST_DEM_EXTENT,
            dem_window_mapper,
            settings.max_window_cells,
            nodata=TEST_NODATA,
        )
        steep_case = AnalyzeArea(
            DemTerrainRepository(datasource),
            SlopeCalculator(),
            STEEP_MIN_DEG,
        )
        stats = steep_case.execute(_bbox(77.45, 18.45, 77.55, 18.55))
        assert stats.slope_deg.min >= STEEP_MIN_DEG
        assert stats.steep_fraction == 1.0


class TestExpectedFailures:
    def test_inverted_bbox_raises(self) -> None:
        with pytest.raises(DomainValidationError):
            _bbox(77.51, 18.51, 77.49, 18.49)

    def test_degenerate_bbox_raises(self) -> None:
        with pytest.raises(DomainValidationError):
            _bbox(77.5, 18.49, 77.5, 18.51)

    def test_bbox_fully_outside_extent_raises(
        self, use_case: AnalyzeArea
    ) -> None:
        with pytest.raises(NoCoverageError):
            use_case.execute(_bbox(80.0, 18.0, 81.0, 19.0))

    def test_nodata_only_window_raises(
        self, use_case: AnalyzeArea
    ) -> None:
        # Tiny bbox over the nodata cell (5, 5) -> all-NaN window.
        with pytest.raises(NoCoverageError):
            use_case.execute(_bbox(77.452, 18.547, 77.453, 18.548))

    def test_window_without_computable_slopes_raises(
        self, use_case: AnalyzeArea
    ) -> None:
        # 1x1 window over cell (10, 10): valid elevation but no neighbour,
        # so every slope cell is NaN.
        with pytest.raises(NoCoverageError):
            use_case.execute(_bbox(77.4998, 18.4998, 77.5002, 18.5002))

    def test_failing_datasource_raises(self) -> None:
        failing_case = AnalyzeArea(
            DemTerrainRepository(FailingRasterDatasource()),
            SlopeCalculator(),
            STEEP_MIN_DEG,
        )
        with pytest.raises(UpstreamDatasourceError):
            failing_case.execute(_bbox(77.49, 18.49, 77.51, 18.51))
