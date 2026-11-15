import math

import pytest

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError

MARS_RADIUS_M = 3_396_190.0


class TestDistance:
    def test_one_degree_of_latitude_on_mars(self):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)

        distance = calculator.distance_m(
            GeoPoint(lat=0.0, lon=0.0), GeoPoint(lat=1.0, lon=0.0)
        )

        expected = math.pi * MARS_RADIUS_M / 180.0  # ~59 274.69 m
        assert distance == pytest.approx(expected, rel=1e-6)

    def test_zero_distance_for_same_point(self):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)
        point = GeoPoint(lat=-4.6, lon=137.44)

        assert calculator.distance_m(point, point) == 0.0

    def test_distance_is_symmetric(self):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)
        a = GeoPoint(lat=-14.5, lon=120.3)
        b = GeoPoint(lat=22.1, lon=-45.0)

        assert calculator.distance_m(a, b) == pytest.approx(
            calculator.distance_m(b, a), rel=1e-12
        )

    @pytest.mark.parametrize("bad_radius", [0.0, -1.0, math.nan, math.inf])
    def test_invalid_radius_raises(self, bad_radius):
        with pytest.raises(RasterValidationError):
            DistanceCalculator(radius_m=bad_radius)


class TestInterpolate:
    def test_midpoint(self):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)
        a = GeoPoint(lat=0.0, lon=0.0)
        b = GeoPoint(lat=2.0, lon=4.0)

        mid = calculator.interpolate(a, b, 0.5)

        assert mid.lat == pytest.approx(1.0)
        assert mid.lon == pytest.approx(2.0)

    def test_endpoints(self):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)
        a = GeoPoint(lat=10.0, lon=20.0)
        b = GeoPoint(lat=30.0, lon=40.0)

        assert calculator.interpolate(a, b, 0.0) == a
        assert calculator.interpolate(a, b, 1.0) == b

    @pytest.mark.parametrize("bad_fraction", [-0.1, 1.1, math.nan, math.inf])
    def test_fraction_out_of_range_raises(self, bad_fraction):
        calculator = DistanceCalculator(radius_m=MARS_RADIUS_M)
        a = GeoPoint(lat=0.0, lon=0.0)
        b = GeoPoint(lat=1.0, lon=1.0)

        with pytest.raises(RasterValidationError):
            calculator.interpolate(a, b, bad_fraction)
