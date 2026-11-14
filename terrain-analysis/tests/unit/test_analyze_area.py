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

        # With the 1-cell halo, every core cell — including corners — is
        # computed from real DEM neighbours, so on a plane all nine cells
        # report the exact plane slope.
        window = repository.window_for(bbox)
        expected = _full_plane_slope_deg(window)
        assert stats.slope_deg.min == pytest.approx(expected)
        assert stats.slope_deg.max == pytest.approx(expected)
        assert stats.slope_deg.mean == pytest.approx(expected)
        assert stats.steep_fraction == 0.0


class TestEdgeCases:
    def test_bbox_partially_outside_extent_is_clipped(
        self, use_case: AnalyzeArea, repository: DemTerrainRepository
    ) -> None:
        # min_lon 77.35 lies west of the DEM edge: clipped to cols 0..4,
        # rows 5..15 (centres within lat 18.45..18.55).
        bbox = _bbox(77.35, 18.45, 77.45, 18.55)
        stats = use_case.execute(bbox)

        rows, cols = np.indices((21, 21))
        expected = 500.0 + 2.0 * cols - 3.0 * rows
        clipped = expected[5:16, 0:5]
        assert stats.elevation_m.min == pytest.approx(float(np.min(clipped)))
        assert stats.elevation_m.max == pytest.approx(float(np.max(clipped)))
        assert stats.elevation_m.mean == pytest.approx(float(np.mean(clipped)))

        # On the plane every core cell has a computable slope equal to the
        # true plane gradient — including the west-edge cells, whose missing
        # neighbours are mirror-extrapolated exactly for planar terrain.
        expected_slope = _full_plane_slope_deg(repository.window_for(bbox))
        for value in (
            stats.slope_deg.min,
            stats.slope_deg.max,
            stats.slope_deg.mean,
        ):
            assert math.isfinite(value)
            assert value == pytest.approx(expected_slope)
        assert stats.steep_fraction == pytest.approx(0.0)

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

    def test_single_cell_bbox_resolves_slope_via_halo(
        self, use_case: AnalyzeArea
    ) -> None:
        # 1x1 core over cell (10, 10): the 1-cell halo supplies real DEM
        # neighbours, so the single core cell gets a computable slope.
        stats = use_case.execute(_bbox(77.4998, 18.4998, 77.5002, 18.5002))
        assert stats.elevation_m.min == pytest.approx(490.0)
        assert stats.slope_deg.min == pytest.approx(stats.slope_deg.max)
        assert stats.slope_deg.min > 0.0

    def test_isolated_cell_without_neighbours_raises(
        self, dem_window_mapper: DemWindowMapper, settings: Settings
    ) -> None:
        # 5x5 DEM where every cell is nodata except (2, 2): even with the
        # halo there is no valid neighbour, so the slope is undefined.
        elevation = np.full((5, 5), TEST_NODATA)
        elevation[2, 2] = 100.0
        datasource = SyntheticDemDatasource(
            elevation,
            TEST_DEM_EXTENT,
            dem_window_mapper,
            settings.max_window_cells,
            nodata=TEST_NODATA,
        )
        isolated_case = AnalyzeArea(
            DemTerrainRepository(datasource),
            SlopeCalculator(),
            STEEP_MIN_DEG,
        )
        with pytest.raises(NoCoverageError):
            isolated_case.execute(_bbox(77.495, 18.495, 77.505, 18.505))

    def test_failing_datasource_raises(self) -> None:
        failing_case = AnalyzeArea(
            DemTerrainRepository(FailingRasterDatasource()),
            SlopeCalculator(),
            STEEP_MIN_DEG,
        )
        with pytest.raises(UpstreamDatasourceError):
            failing_case.execute(_bbox(77.49, 18.49, 77.51, 18.51))


def _bowl_datasource(
    dem_window_mapper: DemWindowMapper, settings: Settings
) -> SyntheticDemDatasource:
    """Non-planar 21x21 DEM: elevation[r, c] = 1.5(r-10)^2 + 2.5(c-10)^2,
    a quadratic bowl whose true slope varies from cell to cell."""
    rows, cols = np.indices((21, 21))
    elevation = 1.5 * (rows - 10.0) ** 2 + 2.5 * (cols - 10.0) ** 2
    return SyntheticDemDatasource(
        elevation,
        TEST_DEM_EXTENT,
        dem_window_mapper,
        settings.max_window_cells,
    )


class TestHaloSlopeAccuracy:
    """Review M1: slope at core border cells must use real DEM
    neighbours, not mirror extrapolation — on non-planar terrain that is
    only achievable with a halo of real cells around the bbox window."""

    @pytest.fixture
    def bowl_repository(
        self, dem_window_mapper: DemWindowMapper, settings: Settings
    ) -> DemTerrainRepository:
        return DemTerrainRepository(
            _bowl_datasource(dem_window_mapper, settings)
        )

    def test_border_cell_slope_equals_interior_computation(
        self, bowl_repository: DemTerrainRepository
    ) -> None:
        use_case = AnalyzeArea(
            bowl_repository, SlopeCalculator(), STEEP_MIN_DEG
        )
        # Reference: slope of every cell computed on the whole DEM, i.e.
        # with its true 3x3 neighbourhood.
        full = bowl_repository.window_for(
            _bbox(77.4, 18.4, 77.6, 18.6)
        )
        reference = SlopeCalculator().compute(full)

        # 3x3 core (cells rows/cols 9..11): every cell is on the window
        # border, so without the halo their slopes would be extrapolated.
        stats = use_case.execute(_bbox(77.49, 18.49, 77.51, 18.51))
        core_slopes = reference[9:12, 9:12]
        assert stats.slope_deg.min == pytest.approx(
            float(np.nanmin(core_slopes))
        )
        assert stats.slope_deg.max == pytest.approx(
            float(np.nanmax(core_slopes))
        )
        assert stats.slope_deg.mean == pytest.approx(
            float(np.nanmean(core_slopes))
        )

    def test_single_cell_bbox_matches_large_window_slope(
        self, bowl_repository: DemTerrainRepository
    ) -> None:
        # The same cell must report the same slope whether it is the sole
        # cell of a tiny bbox or an interior cell of a large window.
        use_case = AnalyzeArea(
            bowl_repository, SlopeCalculator(), STEEP_MIN_DEG
        )
        full = bowl_repository.window_for(
            _bbox(77.4, 18.4, 77.6, 18.6)
        )
        reference = SlopeCalculator().compute(full)
        expected = float(reference[10, 10])

        stats = use_case.execute(
            _bbox(77.4998, 18.4998, 77.5002, 18.5002)
        )
        assert stats.slope_deg.min == pytest.approx(expected)
        assert stats.slope_deg.max == pytest.approx(expected)
        assert stats.slope_deg.mean == pytest.approx(expected)
