"""Unit tests for domain.geo (Mars coordinate rules)."""

import math

import pytest

from location_service.domain.geo import (
    MARSV_RADIUS_M,
    bbox_contains,
    haversine_m,
    normalize_lon,
    validate_lat_lon,
)


class TestNormalizeLon:
    def test_negative_wrapped(self):
        # golden case 18: lon=-222.6 -> 137.4
        assert normalize_lon(-222.6) == pytest.approx(137.4)

    def test_already_east(self):
        assert normalize_lon(137.4417) == pytest.approx(137.4417)

    def test_360_wraps_to_zero(self):
        assert normalize_lon(360.0) == pytest.approx(0.0)

    def test_negative_small(self):
        assert normalize_lon(-0.5) == pytest.approx(359.5)

    def test_over_360(self):
        assert normalize_lon(720.3) == pytest.approx(0.3)

    def test_result_in_range(self):
        for lon in (-720.0, -180.0, -1.0, 0.0, 179.9, 180.0, 359.9, 360.0, 720.0):
            assert 0.0 <= normalize_lon(lon) < 360.0


class TestValidateLatLon:
    def test_valid(self):
        lat, lon = validate_lat_lon(-4.5895, 137.4417)
        assert lat == -4.5895
        assert lon == pytest.approx(137.4417)

    def test_normalizes_lon(self):
        _, lon = validate_lat_lon(-4.5, -222.6)
        assert lon == pytest.approx(137.4)

    @pytest.mark.parametrize("lat", [-90.0, 90.0, 0.0, -4.5895])
    def test_lat_bounds_inclusive(self, lat):
        validate_lat_lon(lat, 0.0)

    @pytest.mark.parametrize("lat", [90.0001, -90.0001, 95.0, -95.0])
    def test_lat_out_of_range(self, lat):
        with pytest.raises(ValueError, match="lat"):
            validate_lat_lon(lat, 0.0)

    @pytest.mark.parametrize("lon", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite(self, lon):
        with pytest.raises(ValueError):
            validate_lat_lon(0.0, lon)

    def test_nan_lat(self):
        with pytest.raises(ValueError):
            validate_lat_lon(float("nan"), 0.0)


class TestHaversine:
    def test_one_degree_latitude(self):
        # 1 deg latitude ~ 59,274.7 m on Mars (R = 3,396,190 m)
        d = haversine_m(0.0, 0.0, 1.0, 0.0)
        assert d == pytest.approx(59274.7, rel=1e-4)

    def test_symmetry(self):
        a = (-4.5895, 137.4417)
        b = (-4.7303, 137.3835)
        assert haversine_m(*a, *b) == pytest.approx(haversine_m(*b, *a))

    def test_same_point_zero(self):
        assert haversine_m(10.0, 200.0, 10.0, 200.0) == 0.0

    def test_antipodal(self):
        d = haversine_m(0.0, 0.0, 0.0, 180.0)
        assert d == pytest.approx(math.pi * MARSV_RADIUS_M, rel=1e-6)

    def test_known_bradbury_glen_etive(self):
        # Bradbury Landing -> Glen Etive straight-line distance is ~9.03 km.
        # NOTE: the plan's example (14420.3 m / "14-15 km") does not match the
        # actual coordinates; documented in docs/DECISIONS.md.
        d = haversine_m(-4.5895, 137.4417, -4.7303, 137.3835)
        assert d == pytest.approx(9026.4, abs=5.0)

    def test_independent_calculation(self):
        # independent haversine reimplementation for cross-check
        lat1, lon1, lat2, lon2 = map(math.radians, (-4.5895, 137.4417, -4.7303, 137.3835))
        h = (
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
        expected = 2 * MARSV_RADIUS_M * math.asin(math.sqrt(h))
        assert haversine_m(-4.5895, 137.4417, -4.7303, 137.3835) == pytest.approx(
            expected, rel=1e-12
        )


class TestBboxContains:
    BBOX = (137.345, -4.739427, 137.454322, -4.58)  # west, south, east, north

    def test_inside(self):
        assert bbox_contains(self.BBOX, -4.668, 137.3703) is True

    def test_outside_lat(self):
        assert bbox_contains(self.BBOX, -5.0, 137.4) is False

    def test_outside_lon(self):
        assert bbox_contains(self.BBOX, -4.6, 130.0) is False

    def test_boundary(self):
        assert bbox_contains(self.BBOX, -4.739427, 137.345) is True
        assert bbox_contains(self.BBOX, -4.58, 137.454322) is True

    def test_normalizes_lon_before_check(self):
        # lon -222.6 -> 137.4 inside bbox
        assert bbox_contains(self.BBOX, -4.6, -222.6) is True
