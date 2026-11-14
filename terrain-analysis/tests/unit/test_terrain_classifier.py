import math

import pytest

from app.core.domain.terrain_class import TerrainClass
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.errors.exceptions import DomainValidationError


class TestClassify:
    @pytest.mark.parametrize(
        ("slope_deg", "expected"),
        [
            (0.0, TerrainClass.FLAT),
            (4.999, TerrainClass.FLAT),
            (5.0, TerrainClass.MODERATE),
            (12.0, TerrainClass.MODERATE),
            (14.999, TerrainClass.MODERATE),
            (15.0, TerrainClass.STEEP),
            (29.999, TerrainClass.STEEP),
            (30.0, TerrainClass.HAZARDOUS),
            (89.9, TerrainClass.HAZARDOUS),
        ],
    )
    def test_default_thresholds(self, slope_deg, expected):
        assert TerrainClassifier().classify(slope_deg) == expected

    def test_class_returns_str_enum_values(self):
        assert TerrainClassifier().classify(12.0) == "moderate"
        assert TerrainClass.HAZARDOUS.value == "hazardous"

    def test_custom_thresholds(self):
        classifier = TerrainClassifier(
            flat_max_deg=2.0, moderate_max_deg=10.0, steep_max_deg=20.0
        )

        assert classifier.classify(1.0) == TerrainClass.FLAT
        assert classifier.classify(12.0) == TerrainClass.STEEP
        assert classifier.classify(25.0) == TerrainClass.HAZARDOUS

    @pytest.mark.parametrize(
        "bad_slope",
        [-0.001, -45.0, math.nan, math.inf, -math.inf, "12", None],
    )
    def test_negative_nan_non_finite_or_non_numeric_raises(self, bad_slope):
        with pytest.raises(DomainValidationError):
            TerrainClassifier().classify(bad_slope)


class TestThresholdValidation:
    @pytest.mark.parametrize(
        ("flat_max", "moderate_max", "steep_max"),
        [
            (15.0, 5.0, 30.0),   # flat >= moderate
            (5.0, 5.0, 30.0),    # equal boundary
            (5.0, 30.0, 30.0),   # moderate == steep
            (5.0, 15.0, 10.0),   # steep below moderate
            (0.0, 10.0, 20.0),   # non-positive
            (-1.0, 10.0, 20.0),  # negative
            (5.0, math.nan, 30.0),
        ],
    )
    def test_invalid_ordering_raises(self, flat_max, moderate_max, steep_max):
        with pytest.raises(DomainValidationError):
            TerrainClassifier(
                flat_max_deg=flat_max,
                moderate_max_deg=moderate_max,
                steep_max_deg=steep_max,
            )
