import math

import pytest

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sample import PathSample
from app.core.ports.raster_repository import RasterRepository
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    NoCoverageError,
    RasterValidationError,
    UnknownBandError,
    UnknownDatasetError,
)
from app.features.path_sampling.application.sample_path import SamplePath
from app.features.path_sampling.domain.path_profile import PathProfile
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8 cols
# of 0.01 deg. Band "slope_deg" holds row*10 + col (nodata at cell (1,1)).
# A meridian path down column 0 crosses rows 0..9 -> values 0,10,...,90.
MARS_RADIUS_M = 3_396_190.0
METERS_PER_DEG_LAT = math.pi * MARS_RADIUS_M / 180.0
RESOLUTION_M = 0.01 * METERS_PER_DEG_LAT


def meridian_path(lat0: float, lat1: float, lon: float = 137.405):
    return [GeoPoint(lat=lat0, lon=lon), GeoPoint(lat=lat1, lon=lon)]


class _CountingRepository(RasterRepository):
    """Spy delegating to a real repository, counting read_cells calls."""

    def __init__(self, inner: RasterRepository) -> None:
        self._inner = inner
        self.read_calls = 0

    def dataset_names(self):
        return self._inner.dataset_names()

    def metadata(self, dataset):
        return self._inner.metadata(dataset)

    def read_cells(self, dataset, band, rows, cols):
        self.read_calls += 1
        return self._inner.read_cells(dataset, band, rows, cols)

    def is_readable(self, dataset):
        return self._inner.is_readable(dataset)


class TestSamplePath:
    def test_meridian_path_samples_every_row_with_default_step(
        self, repository
    ):
        path = meridian_path(-4.605, -4.695)

        profile = SamplePath(repository).execute("test", path, "slope_deg")

        assert profile.band == "slope_deg"
        assert len(profile.samples) == 10
        assert len(profile.values) == 10
        assert list(profile.values) == [float(10 * r) for r in range(10)]
        assert profile.samples[0].distance_m == 0.0
        assert profile.samples[0].point.lat == pytest.approx(-4.605)
        assert profile.samples[0].point.lon == pytest.approx(137.405)
        assert profile.samples[-1].point.lat == pytest.approx(-4.695)
        assert profile.samples[-1].distance_m == pytest.approx(
            profile.total_distance_m
        )
        assert profile.total_distance_m == pytest.approx(
            0.09 * METERS_PER_DEG_LAT, rel=1e-9
        )

    def test_explicit_step_skips_rows(self, repository):
        path = meridian_path(-4.605, -4.695)

        profile = SamplePath(repository).execute(
            "test", path, "slope_deg", sample_distance_m=0.05 * METERS_PER_DEG_LAT
        )

        assert len(profile.samples) == 3
        assert list(profile.values) == [0.0, 50.0, 90.0]

    def test_values_are_verbatim_python_floats(self, repository):
        path = meridian_path(-4.605, -4.615)

        profile = SamplePath(repository).execute(
            "test", path, "roughness_m", sample_distance_m=10_000.0
        )

        # Oversized step -> only the two endpoints are sampled.
        assert len(profile.samples) == 2
        assert type(profile.values[0]) is float
        assert profile.values[0] == 100.0  # band 2: 100 + row*10 + col
        assert profile.values[1] == 110.0

    def test_nodata_cell_is_nan_in_domain(self, repository):
        path = [
            GeoPoint(lat=-4.615, lon=137.415),
            GeoPoint(lat=-4.615, lon=137.425),
        ]

        profile = SamplePath(repository).execute(
            "test", path, "slope_deg", sample_distance_m=10_000.0
        )

        assert math.isnan(profile.values[0])  # cell (1, 1) holds the sentinel
        assert profile.values[1] == 12.0

    def test_partially_outside_path_yields_nan_tail(self, repository):
        path = meridian_path(-4.605, -4.595)  # endpoint north of max_lat

        profile = SamplePath(repository).execute("test", path, "slope_deg")

        assert len(profile.samples) == 2
        assert profile.values[0] == 0.0
        assert math.isnan(profile.values[1])

    def test_reads_one_window_for_all_samples(self, repository):
        spy = _CountingRepository(repository)
        path = meridian_path(-4.605, -4.695)

        profile = SamplePath(spy).execute("test", path, "slope_deg")

        assert spy.read_calls == 1
        assert list(profile.values) == [float(10 * r) for r in range(10)]

    def test_last_sample_is_final_vertex_and_total_is_haversine_sum(
        self, repository
    ):
        path = [
            GeoPoint(lat=-4.605, lon=137.405),
            GeoPoint(lat=-4.615, lon=137.415),
            GeoPoint(lat=-4.625, lon=137.415),
        ]

        profile = SamplePath(repository).execute("test", path, "slope_deg")

        calculator = DistanceCalculator(MARS_RADIUS_M)
        expected_total = sum(
            calculator.distance_m(a, b) for a, b in zip(path, path[1:])
        )
        assert profile.total_distance_m == pytest.approx(
            expected_total, rel=1e-12
        )
        last = profile.samples[-1].point
        assert last.lat == pytest.approx(path[-1].lat, abs=1e-9)
        assert last.lon == pytest.approx(path[-1].lon, abs=1e-9)

    def test_fully_outside_path_raises_no_coverage(self, repository):
        path = meridian_path(-4.55, -4.56)

        with pytest.raises(NoCoverageError):
            SamplePath(repository).execute("test", path, "slope_deg")

    def test_single_point_path_raises_validation(self, repository):
        with pytest.raises(RasterValidationError):
            SamplePath(repository).execute(
                "test", [GeoPoint(lat=-4.605, lon=137.405)], "slope_deg"
            )

    @pytest.mark.parametrize("bad_step", [0.0, -1.0])
    def test_non_positive_step_raises_validation(self, repository, bad_step):
        with pytest.raises(RasterValidationError):
            SamplePath(repository).execute(
                "test",
                meridian_path(-4.605, -4.615),
                "slope_deg",
                sample_distance_m=bad_step,
            )

    def test_more_than_max_path_points_raises_validation(self, repository):
        path = [
            GeoPoint(lat=-4.605 - 0.001 * k, lon=137.405) for k in range(4)
        ]

        with pytest.raises(RasterValidationError):
            SamplePath(repository, max_path_points=3).execute(
                "test", path, "slope_deg"
            )

    def test_more_than_max_samples_raises_validation(self, repository):
        with pytest.raises(RasterValidationError):
            SamplePath(repository, max_samples=5).execute(
                "test", meridian_path(-4.605, -4.695), "slope_deg"
            )

    def test_unknown_band_raises_listing_valid_names(self, repository):
        with pytest.raises(UnknownBandError) as excinfo:
            SamplePath(repository).execute(
                "test", meridian_path(-4.605, -4.615), "nope"
            )

        assert "slope_deg" in str(excinfo.value)

    def test_unknown_dataset_raises(self, repository):
        with pytest.raises(UnknownDatasetError):
            SamplePath(repository).execute(
                "nope", meridian_path(-4.605, -4.615), "slope_deg"
            )

    def test_unavailable_dataset_raises(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(DatasetUnavailableError):
            SamplePath(repository).execute(
                "broken", meridian_path(-4.605, -4.615), "slope_deg"
            )

    def test_short_path_fails_before_touching_dataset(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(RasterValidationError):
            SamplePath(repository).execute(
                "broken", [GeoPoint(lat=-4.605, lon=137.405)], "slope_deg"
            )

    def test_too_many_points_fails_before_touching_dataset(
        self, dataset_config
    ):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        path = [
            GeoPoint(lat=-4.605 - 0.001 * k, lon=137.405) for k in range(4)
        ]

        with pytest.raises(RasterValidationError):
            SamplePath(repository, max_path_points=3).execute(
                "broken", path, "slope_deg"
            )


class TestPathProfile:
    def test_rejects_mismatched_samples_and_values(self):
        sample = PathSample(point=GeoPoint(lat=-4.605, lon=137.405), distance_m=0.0)

        with pytest.raises(RasterValidationError):
            PathProfile(
                band="slope_deg",
                total_distance_m=0.0,
                samples=(sample,),
                values=(),
            )

    def test_rejects_empty_samples(self):
        with pytest.raises(RasterValidationError):
            PathProfile(
                band="slope_deg",
                total_distance_m=0.0,
                samples=(),
                values=(),
            )

    def test_rejects_empty_band_name(self):
        sample = PathSample(point=GeoPoint(lat=-4.605, lon=137.405), distance_m=0.0)

        with pytest.raises(RasterValidationError):
            PathProfile(
                band="",
                total_distance_m=0.0,
                samples=(sample,),
                values=(0.0,),
            )
