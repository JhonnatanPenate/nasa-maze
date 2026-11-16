"""PathSampler: regular arc-length sampling, MS3/MS4 semantics."""

import itertools

import pytest
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import DomainValidationError

RADIUS = 3_396_190.0
SAMPLER = PathSampler(DistanceCalculator(RADIUS))
A = GeoPoint(lat=-4.60, lon=137.44)
B = GeoPoint(lat=-4.65, lon=137.42)


def test_samples_include_endpoints() -> None:
    samples = SAMPLER.sample([A, B], step_m=100.0, max_samples=100)
    assert samples[0].distance_m == 0.0
    assert samples[-1].distance_m == pytest.approx(DistanceCalculator(RADIUS).distance_m(A, B))
    assert all(s.point.lat is not None for s in samples)


def test_step_spacing() -> None:
    samples = SAMPLER.sample([A, B], step_m=100.0, max_samples=100)
    gaps = [b.distance_m - a.distance_m for a, b in itertools.pairwise(samples)]
    assert all(g == pytest.approx(100.0) for g in gaps[:-1])


def test_requires_two_points() -> None:
    with pytest.raises(DomainValidationError):
        SAMPLER.sample([A], step_m=100.0, max_samples=100)


def test_rejects_bad_step() -> None:
    for step in (0.0, -5.0, float("nan"), float("inf")):
        with pytest.raises(DomainValidationError):
            SAMPLER.sample([A, B], step_m=step, max_samples=100)


def test_enforces_max_samples() -> None:
    with pytest.raises(DomainValidationError, match="exceeding"):
        SAMPLER.sample([A, B], step_m=1.0, max_samples=10)


def test_zero_length_segment_does_not_crash() -> None:
    samples = SAMPLER.sample([A, A, B], step_m=500.0, max_samples=100)
    assert samples[-1].point == B
