from app.core.domain.geo_point import GeoPoint
from app.features.point_query.domain.point_values import PointValues


class TestPointValues:
    def test_caller_dict_is_not_mutated(self):
        source = {"slope_deg": 1}

        PointValues(point=GeoPoint(lat=0.0, lon=0.0), values=source)

        assert source == {"slope_deg": 1}
        assert isinstance(source["slope_deg"], int)

    def test_values_are_stored_in_a_new_float_dict(self):
        source = {"slope_deg": "1.5"}

        result = PointValues(
            point=GeoPoint(lat=0.0, lon=0.0), values=source
        )

        assert result.values == {"slope_deg": 1.5}
        assert result.values is not source
        assert source == {"slope_deg": "1.5"}
