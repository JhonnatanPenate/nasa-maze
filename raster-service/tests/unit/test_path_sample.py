from dataclasses import FrozenInstanceError

import pytest

from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sample import PathSample


class TestPathSample:
    def test_stores_point_and_distance(self):
        point = GeoPoint(lat=-4.6, lon=137.44)

        sample = PathSample(point=point, distance_m=90.0)

        assert sample.point == point
        assert sample.distance_m == 90.0

    def test_equality(self):
        point = GeoPoint(lat=-4.6, lon=137.44)

        assert PathSample(point=point, distance_m=1.0) == PathSample(
            point=GeoPoint(lat=-4.6, lon=137.44), distance_m=1.0
        )

    def test_is_immutable(self):
        sample = PathSample(
            point=GeoPoint(lat=0.0, lon=0.0), distance_m=0.0
        )

        with pytest.raises(FrozenInstanceError):
            sample.distance_m = 5.0
