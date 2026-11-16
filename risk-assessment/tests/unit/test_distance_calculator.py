"""DistanceCalculator: haversine on the Mars sphere + interpolation."""

import math

import pytest
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import DomainValidationError

RADIUS = 3_396_190.0
CALC = DistanceCalculator(RADIUS)


def test_known_distance() -> None:
    # ~0.01 deg latitude at the equator-ish latitude: sanity magnitude only.
    a = GeoPoint(lat=0.0, lon=0.0)
    b = GeoPoint(lat=0.0, lon=0.01)
    d = CALC.distance_m(a, b)
    expected = RADIUS * math.radians(0.01) * math.cos(math.radians(0.0))
    # haversine on sphere: dlon arc * cos(lat)
    assert d == pytest.approx(expected, rel=1e-6)


def test_same_point_is_zero() -> None:
    p = GeoPoint(lat=-4.6, lon=137.4)
    assert CALC.distance_m(p, p) == pytest.approx(0.0)


def test_antipodal_within_pi() -> None:
    a = GeoPoint(lat=0.0, lon=0.0)
    b = GeoPoint(lat=0.0, lon=180.0)
    assert CALC.distance_m(a, b) == pytest.approx(math.pi * RADIUS, rel=1e-6)


def test_interpolate_midpoint() -> None:
    a = GeoPoint(lat=-4.60, lon=137.44)
    b = GeoPoint(lat=-4.65, lon=137.42)
    mid = CALC.interpolate(a, b, 0.5)
    assert mid.lat == pytest.approx(-4.625)
    assert mid.lon == pytest.approx(137.43)


def test_interpolate_bounds() -> None:
    a = GeoPoint(lat=-4.60, lon=137.44)
    b = GeoPoint(lat=-4.65, lon=137.42)
    assert CALC.interpolate(a, b, 0.0) == a
    assert CALC.interpolate(a, b, 1.0) == b


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf"), "x"])
def test_interpolate_rejects_bad_fraction(fraction: object) -> None:
    a = GeoPoint(lat=-4.60, lon=137.44)
    b = GeoPoint(lat=-4.65, lon=137.42)
    with pytest.raises(DomainValidationError):
        CALC.interpolate(a, b, fraction)  # type: ignore[arg-type]


@pytest.mark.parametrize("radius", [0.0, -1.0, float("nan"), "x"])
def test_bad_radius_rejected(radius: object) -> None:
    with pytest.raises(DomainValidationError):
        DistanceCalculator(radius)  # type: ignore[arg-type]
