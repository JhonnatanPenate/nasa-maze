import math
import time

import pytest

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import DomainValidationError

MARS_RADIUS_M = 3_389_500.0
METERS_PER_DEG_LAT = math.pi * MARS_RADIUS_M / 180.0


@pytest.fixture
def sampler() -> PathSampler:
    return PathSampler(DistanceCalculator(radius_m=MARS_RADIUS_M))


def meridian_path(meters: float) -> list[GeoPoint]:
    return [GeoPoint(lat=0.0, lon=0.0), GeoPoint(lat=meters / METERS_PER_DEG_LAT, lon=0.0)]


class TestSample:
    def test_evenly_spaced_samples_on_straight_path(self, sampler):
        path = meridian_path(1000.0)

        samples = sampler.sample(path, step_m=250.0, max_samples=100)

        assert len(samples) == 5
        assert [s.distance_m for s in samples] == pytest.approx(
            [0.0, 250.0, 500.0, 750.0, 1000.0], abs=1e-6
        )
        assert samples[0].point == path[0]
        assert samples[-1].point.lat == pytest.approx(path[-1].lat, abs=1e-9)
        mid = samples[2].point
        assert mid.lat == pytest.approx(path[-1].lat / 2.0, rel=1e-6)
        assert mid.lon == pytest.approx(0.0, abs=1e-12)

    def test_exact_multiple_of_step_has_no_duplicate_endpoint(self, sampler):
        path = meridian_path(1000.0)

        samples = sampler.sample(path, step_m=100.0, max_samples=100)

        assert len(samples) == 11
        assert samples[-1].distance_m == pytest.approx(1000.0, abs=1e-6)
        distances = [s.distance_m for s in samples]
        assert len(distances) == len(set(distances))

    def test_remainder_appends_final_point(self, sampler):
        path = meridian_path(1000.0)

        samples = sampler.sample(path, step_m=300.0, max_samples=100)

        assert [s.distance_m for s in samples] == pytest.approx(
            [0.0, 300.0, 600.0, 900.0, 1000.0], abs=1e-6
        )

    def test_multi_vertex_path_samples_across_vertex(self, sampler):
        leg_m = 500.0
        dlat = leg_m / METERS_PER_DEG_LAT
        vertex = GeoPoint(lat=dlat, lon=0.0)
        dlon = leg_m / (METERS_PER_DEG_LAT * math.cos(math.radians(dlat)))
        path = [GeoPoint(lat=0.0, lon=0.0), vertex, GeoPoint(lat=dlat, lon=dlon)]

        samples = sampler.sample(path, step_m=leg_m, max_samples=100)

        assert len(samples) == 3
        assert samples[1].distance_m == pytest.approx(500.0, abs=1e-6)
        assert samples[1].point.lat == pytest.approx(vertex.lat, abs=1e-9)
        assert samples[1].point.lon == pytest.approx(vertex.lon, abs=1e-9)
        assert samples[-1].point.lon == pytest.approx(dlon, abs=1e-9)

    def test_zero_length_segment_in_middle_does_not_break(self, sampler):
        dlat = 1000.0 / METERS_PER_DEG_LAT
        start = GeoPoint(lat=0.0, lon=0.0)
        path = [start, start, GeoPoint(lat=dlat, lon=0.0)]

        samples = sampler.sample(path, step_m=500.0, max_samples=100)

        assert len(samples) == 3
        assert samples[-1].distance_m == pytest.approx(1000.0, abs=1e-6)

    def test_identical_points_yield_single_sample_at_zero(self, sampler):
        point = GeoPoint(lat=18.4, lon=77.5)

        samples = sampler.sample([point, point, point], step_m=100.0, max_samples=100)

        assert len(samples) == 1
        assert samples[0].distance_m == 0.0
        assert samples[0].point == point

    def test_final_sample_distance_is_clamped_to_total(self, sampler):
        path = meridian_path(1000.0)
        total = DistanceCalculator(radius_m=MARS_RADIUS_M).distance_m(*path)

        samples = sampler.sample(path, step_m=300.0, max_samples=100)

        assert samples[-1].distance_m == total


class TestValidation:
    @pytest.mark.parametrize("bad_step", [0.0, -1.0, math.nan, math.inf])
    def test_non_positive_step_raises(self, sampler, bad_step):
        with pytest.raises(DomainValidationError):
            sampler.sample(meridian_path(1000.0), step_m=bad_step, max_samples=100)

    def test_path_with_fewer_than_two_points_raises(self, sampler):
        with pytest.raises(DomainValidationError):
            sampler.sample([GeoPoint(lat=0.0, lon=0.0)], step_m=100.0, max_samples=100)
        with pytest.raises(DomainValidationError):
            sampler.sample([], step_m=100.0, max_samples=100)

    def test_exceeding_max_samples_raises(self, sampler):
        with pytest.raises(DomainValidationError):
            sampler.sample(meridian_path(1000.0), step_m=100.0, max_samples=10)

    def test_excessive_sample_count_rejected_before_generation(self, sampler):
        # ~592 km at 1 mm steps would need ~592 million samples; the count
        # check must run arithmetically before any list is built.
        path = meridian_path(592_000.0)

        start = time.perf_counter()
        with pytest.raises(DomainValidationError):
            sampler.sample(path, step_m=0.001, max_samples=1000)
        assert time.perf_counter() - start < 1.0

    @pytest.mark.parametrize("bad_max", [0, -3, 1.5, "10", True, None])
    def test_invalid_max_samples_raises(self, sampler, bad_max):
        with pytest.raises(DomainValidationError):
            sampler.sample(meridian_path(10.0), step_m=5.0, max_samples=bad_max)

    def test_max_samples_boundary_is_allowed(self, sampler):
        samples = sampler.sample(meridian_path(1000.0), step_m=250.0, max_samples=5)

        assert len(samples) == 5
