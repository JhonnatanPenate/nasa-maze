import math

import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError


class TestBoundingBox:
    def test_valid_box_stores_extent(self):
        bbox = BoundingBox(min_lon=137.345, min_lat=-4.74, max_lon=137.455, max_lat=-4.58)

        assert bbox.min_lon == 137.345
        assert bbox.min_lat == -4.74
        assert bbox.max_lon == 137.455
        assert bbox.max_lat == -4.58

    def test_inverted_lon_raises(self):
        with pytest.raises(RasterValidationError):
            BoundingBox(min_lon=137.455, min_lat=-4.74, max_lon=137.345, max_lat=-4.58)

    def test_inverted_lat_raises(self):
        with pytest.raises(RasterValidationError):
            BoundingBox(min_lon=137.345, min_lat=-4.58, max_lon=137.455, max_lat=-4.74)

    @pytest.mark.parametrize(
        ("min_lon", "min_lat", "max_lon", "max_lat"),
        [
            (137.345, -4.74, 137.345, -4.58),  # degenerate lon
            (137.345, -4.74, 137.455, -4.74),  # degenerate lat
            (137.345, -4.74, 137.345, -4.74),  # single point
        ],
    )
    def test_degenerate_box_raises(self, min_lon, min_lat, max_lon, max_lat):
        with pytest.raises(RasterValidationError):
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
        with pytest.raises(RasterValidationError):
            BoundingBox(
                min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
            )

    def test_antimeridian_crossing_box_is_rejected(self):
        with pytest.raises(RasterValidationError):
            BoundingBox(min_lon=170.0, min_lat=-10.0, max_lon=-170.0, max_lat=10.0)

    def test_contains_inside_boundary_and_outside(self):
        bbox = BoundingBox(min_lon=137.4, min_lat=-4.7, max_lon=137.45, max_lat=-4.6)

        assert bbox.contains(GeoPoint(lat=-4.65, lon=137.42)) is True
        assert bbox.contains(GeoPoint(lat=-4.7, lon=137.4)) is True  # corner, inclusive
        assert bbox.contains(GeoPoint(lat=-4.6, lon=137.45)) is True  # max edge
        assert bbox.contains(GeoPoint(lat=-4.71, lon=137.42)) is False
        assert bbox.contains(GeoPoint(lat=-4.65, lon=137.46)) is False
