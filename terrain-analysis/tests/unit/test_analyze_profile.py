from unittest.mock import Mock

import numpy as np
import pytest

from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.config.settings import Settings
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)
from app.core.ports.raster_datasource import RasterDatasource
from app.features.profile_analysis.application.analyze_profile import (
    AnalyzeProfile,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
from tests.fakes.fake_slope_terrain_repository import (
    FakeSlopeTerrainRepository,
)

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
def use_case_factory(settings: Settings):
    """Builds an AnalyzeProfile over a real DemTerrainRepository, allowing
    per-test overrides of the configured limits."""

    def factory(
        datasource: RasterDatasource,
        max_path_points: int | None = None,
        max_samples: int | None = None,
    ) -> AnalyzeProfile:
        distance_calculator = DistanceCalculator(
            settings.planet_radius_km * 1000.0
        )
        return AnalyzeProfile(
            sampler=TerrainPointSampler(
                DemTerrainRepository(datasource), SlopeCalculator()
            ),
            path_sampler=PathSampler(distance_calculator),
            max_path_points=(
                settings.max_path_points
                if max_path_points is None
                else max_path_points
            ),
            max_samples=(
                settings.max_samples if max_samples is None else max_samples
            ),
        )

    return factory


def test_profile_along_plane_returns_expected_aggregates(
    use_case_factory, synthetic_datasource, settings
):
    """Due-south path on the test plane (elevation = 500 + 2c - 3r, row 0 at
    max lat): heading south descends 3 m per cell, so all loss, no gain."""
    use_case = use_case_factory(synthetic_datasource)
    start = GeoPoint(lat=18.55, lon=77.5)
    end = GeoPoint(lat=18.45, lon=77.5)

    profile = use_case.execute([start, end], sample_distance_m=2000.0)

    expected_total = DistanceCalculator(
        settings.planet_radius_km * 1000.0
    ).distance_m(start, end)
    assert profile.sample_count == 4
    assert len(profile.samples) == 4
    assert profile.total_distance_m == pytest.approx(expected_total)
    assert [s.distance_m for s in profile.samples] == pytest.approx(
        [0.0, 2000.0, 4000.0, expected_total]
    )
    # Samples stay at lon 77.5 -> grid column 10 -> elevation 520 - 3*row.
    assert [s.elevation_m for s in profile.samples] == pytest.approx(
        [505.0, 496.0, 484.0, 475.0]
    )
    assert profile.elevation_gain_m == pytest.approx(0.0)
    assert profile.elevation_loss_m == pytest.approx(30.0)
    assert all(s.slope_deg > 0.0 for s in profile.samples)
    assert 0.0 < profile.max_slope_deg < 1.0
    assert profile.max_slope_deg == pytest.approx(
        max(s.slope_deg for s in profile.samples)
    )


def test_profile_northwards_reports_gain_not_loss(
    use_case_factory, synthetic_datasource
):
    use_case = use_case_factory(synthetic_datasource)
    profile = use_case.execute(
        [GeoPoint(lat=18.45, lon=77.5), GeoPoint(lat=18.55, lon=77.5)],
        sample_distance_m=2000.0,
    )
    assert profile.elevation_gain_m == pytest.approx(30.0)
    assert profile.elevation_loss_m == pytest.approx(0.0)


def test_degenerate_path_of_identical_points_returns_single_sample(
    use_case_factory, synthetic_datasource
):
    use_case = use_case_factory(synthetic_datasource)
    point = GeoPoint(lat=18.5, lon=77.5)

    profile = use_case.execute([point, point], sample_distance_m=100.0)

    assert profile.sample_count == 1
    assert profile.total_distance_m == pytest.approx(0.0)
    assert profile.elevation_gain_m == pytest.approx(0.0)
    assert profile.elevation_loss_m == pytest.approx(0.0)
    sample = profile.samples[0]
    assert sample.distance_m == pytest.approx(0.0)
    # lat 18.5, lon 77.5 -> cell (10, 10) -> 500 + 20 - 30.
    assert sample.elevation_m == pytest.approx(490.0)
    assert sample.slope_deg > 0.0


def test_path_exceeding_max_path_points_is_rejected(
    use_case_factory, synthetic_datasource, settings
):
    use_case = use_case_factory(synthetic_datasource)
    path = [GeoPoint(lat=18.5, lon=77.5)] * (settings.max_path_points + 1)

    with pytest.raises(DomainValidationError):
        use_case.execute(path, sample_distance_m=100.0)


def test_sampling_exceeding_max_samples_is_rejected(
    use_case_factory, synthetic_datasource
):
    use_case = use_case_factory(synthetic_datasource, max_samples=5)
    path = [GeoPoint(lat=18.55, lon=77.5), GeoPoint(lat=18.45, lon=77.5)]

    with pytest.raises(DomainValidationError):
        use_case.execute(path, sample_distance_m=1000.0)


def test_non_positive_sample_distance_is_rejected(
    use_case_factory, synthetic_datasource
):
    use_case = use_case_factory(synthetic_datasource)
    path = [GeoPoint(lat=18.55, lon=77.5), GeoPoint(lat=18.45, lon=77.5)]

    with pytest.raises(DomainValidationError):
        use_case.execute(path, sample_distance_m=0.0)


def test_sample_on_nodata_cell_raises_no_coverage(
    use_case_factory, synthetic_datasource
):
    """The nodata cell is (row 5, col 5); a sample at its centre must fail
    the whole profile."""
    use_case = use_case_factory(synthetic_datasource)
    path = [GeoPoint(lat=18.55, lon=77.45), GeoPoint(lat=18.55, lon=77.46)]

    with pytest.raises(NoCoverageError):
        use_case.execute(path, sample_distance_m=100.0)


def test_path_outside_extent_raises_no_coverage(
    use_case_factory, synthetic_datasource
):
    use_case = use_case_factory(synthetic_datasource)
    path = [GeoPoint(lat=18.7, lon=77.5), GeoPoint(lat=18.71, lon=77.5)]

    with pytest.raises(NoCoverageError):
        use_case.execute(path, sample_distance_m=100.0)


def test_failing_datasource_raises_upstream_error(use_case_factory):
    use_case = use_case_factory(FailingRasterDatasource())
    path = [GeoPoint(lat=18.55, lon=77.5), GeoPoint(lat=18.45, lon=77.5)]

    with pytest.raises(UpstreamDatasourceError):
        use_case.execute(path, sample_distance_m=100.0)


class TestGridMode:
    """Grid mode: samples carry slope from the band and elevation_m=None,
    so gain/loss must be None instead of a fabricated 0."""

    @pytest.fixture
    def slope_calculator(self) -> Mock:
        return Mock(spec=SlopeCalculator)

    @pytest.fixture
    def grid_use_case(
        self, settings: Settings, slope_calculator: Mock
    ) -> AnalyzeProfile:
        return AnalyzeProfile(
            sampler=TerrainPointSampler(
                FakeSlopeTerrainRepository(GRID_SLOPE, GRID_EXTENT),
                slope_calculator,
            ),
            path_sampler=PathSampler(
                DistanceCalculator(settings.planet_radius_km * 1000.0)
            ),
            max_path_points=settings.max_path_points,
            max_samples=settings.max_samples,
        )

    def test_samples_carry_slope_and_null_elevation(
        self, grid_use_case: AnalyzeProfile, slope_calculator: Mock
    ) -> None:
        # Due-north path along lon 100.5 (grid column 0), 4 degrees:
        # samples climb from slope 21 deg down to 1 deg.
        profile = grid_use_case.execute(
            [GeoPoint(lat=-9.5, lon=100.5), GeoPoint(lat=-5.5, lon=100.5)],
            sample_distance_m=50000.0,
        )

        assert profile.sample_count > 1
        assert all(s.elevation_m is None for s in profile.samples)
        assert profile.elevation_gain_m is None
        assert profile.elevation_loss_m is None
        assert all(s.slope_deg >= 0.0 for s in profile.samples)
        assert profile.max_slope_deg == pytest.approx(21.0)
        slope_calculator.compute_at_center.assert_not_called()
        slope_calculator.compute.assert_not_called()

    def test_path_through_nodata_cell_raises_no_coverage(
        self, grid_use_case: AnalyzeProfile
    ) -> None:
        # Cell (2, 2) is nodata; the first path sample lands in it.
        path = [
            GeoPoint(lat=-7.5, lon=102.4),
            GeoPoint(lat=-7.5, lon=102.6),
        ]
        with pytest.raises(NoCoverageError):
            grid_use_case.execute(path, sample_distance_m=1000.0)

    def test_path_outside_extent_raises_no_coverage(
        self, grid_use_case: AnalyzeProfile
    ) -> None:
        path = [GeoPoint(lat=0.0, lon=100.5), GeoPoint(lat=0.1, lon=100.5)]
        with pytest.raises(NoCoverageError):
            grid_use_case.execute(path, sample_distance_m=1000.0)
