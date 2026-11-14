import pytest

from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.config.settings import Settings
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
