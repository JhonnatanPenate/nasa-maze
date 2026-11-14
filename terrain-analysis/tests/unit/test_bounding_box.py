import math

import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import DomainValidationError


class TestBoundingBox:
    def test_valid_box_stores_extent(self):
        bbox = BoundingBox(min_lon=77.5, min_lat=18.4, max_lon=77.6, max_lat=18.5)

        assert bbox.min_lon == 77.5
        assert bbox.min_lat == 18.4
        assert bbox.max_lon == 77.6
        assert bbox.max_lat == 18.5

    def test_inverted_lon_raises(self):
        with pytest.raises(DomainValidationError):
            BoundingBox(min_lon=77.6, min_lat=18.4, max_lon=77.5, max_lat=18.5)

    def test_inverted_lat_raises(self):
        with pytest.raises(DomainValidationError):
            BoundingBox(min_lon=77.5, min_lat=18.5, max_lon=77.6, max_lat=18.4)

    @pytest.mark.parametrize(
        ("min_lon", "min_lat", "max_lon", "max_lat"),
        [
            (77.5, 18.4, 77.5, 18.5),  # degenerate lon
            (77.5, 18.4, 77.6, 18.4),  # degenerate lat
            (77.5, 18.4, 77.5, 18.4),  # single point
        ],
    )
    def test_degenerate_box_raises(self, min_lon, min_lat, max_lon, max_lat):
        with pytest.raises(DomainValidationError):
            BoundingBox(
                min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
            )

    @pytest.mark.parametrize(
        ("min_lon", "min_lat", "max_lon", "max_lat"),
        [
            (-181.0, 0.0, 0.0, 1.0),
            (0.0, -91.0, 1.0, 0.0),
            (0.0, 0.0, 181.0, 1.0),
            (0.0, 0.0, 1.0, 91.0),
            (math.nan, 0.0, 1.0, 1.0),
            (0.0, 0.0, math.inf, 1.0),
        ],
    )
    def test_out_of_range_or_non_finite_raises(
        self, min_lon, min_lat, max_lon, max_lat
    ):
        with pytest.raises(DomainValidationError):
            BoundingBox(
                min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
            )

    def test_antimeridian_crossing_box_is_rejected(self):
        # A box intended to span the antimeridian (min_lon > max_lon when
        # read as west→east) is rejected as inverted; crossing is unsupported.
        with pytest.raises(DomainValidationError):
            BoundingBox(min_lon=170.0, min_lat=-10.0, max_lon=-170.0, max_lat=10.0)

    def test_contains_inside_boundary_and_outside(self):
        bbox = BoundingBox(min_lon=77.5, min_lat=18.4, max_lon=77.6, max_lat=18.5)

        assert bbox.contains(GeoPoint(lat=18.45, lon=77.55)) is True
        assert bbox.contains(GeoPoint(lat=18.4, lon=77.5)) is True  # corner, inclusive
        assert bbox.contains(GeoPoint(lat=18.5, lon=77.6)) is True  # max edge, inclusive
        assert bbox.contains(GeoPoint(lat=18.39, lon=77.55)) is False
        assert bbox.contains(GeoPoint(lat=18.45, lon=77.61)) is False
