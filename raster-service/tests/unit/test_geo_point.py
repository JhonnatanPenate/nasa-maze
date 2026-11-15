import math

import pytest

from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import RasterValidationError


class TestGeoPoint:
    def test_valid_point_stores_coordinates(self):
        point = GeoPoint(lat=-4.6, lon=137.44)

        assert point.lat == -4.6
        assert point.lon == 137.44

    def test_boundary_values_are_accepted(self):
        assert GeoPoint(lat=90.0, lon=180.0).lat == 90.0
        assert GeoPoint(lat=-90.0, lon=-180.0).lon == -180.0

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [
            (90.0001, 0.0),
            (-90.0001, 0.0),
            (0.0, 180.0001),
            (0.0, -180.0001),
            (1e6, 0.0),
            (0.0, -1e6),
        ],
    )
    def test_out_of_range_raises(self, lat, lon):
        with pytest.raises(RasterValidationError):
            GeoPoint(lat=lat, lon=lon)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_raises(self, bad):
        with pytest.raises(RasterValidationError):
            GeoPoint(lat=bad, lon=0.0)
        with pytest.raises(RasterValidationError):
            GeoPoint(lat=0.0, lon=bad)
