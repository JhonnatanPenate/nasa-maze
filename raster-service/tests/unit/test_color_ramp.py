import numpy as np
import pytest

from app.core.domain.color_ramp import ColorRamp
from app.core.errors.exceptions import RasterValidationError


class TestNamedRamps:
    def test_known_ramp_names(self):
        assert set(ColorRamp.names()) == {"slope", "viridis", "grayscale"}

    def test_slope_endpoints(self):
        rgba = ColorRamp("slope").render(
            np.array([[0.0, 35.0]]), value_min=0.0, value_max=35.0
        )

        assert rgba.shape == (1, 2, 4)
        assert rgba.dtype == np.uint8
        assert tuple(rgba[0, 0]) == (0, 128, 0, 255)
        assert tuple(rgba[0, 1]) == (255, 0, 0, 255)

    def test_slope_midpoint_is_yellow(self):
        rgba = ColorRamp("slope").render(
            np.array([[17.5]]), value_min=0.0, value_max=35.0
        )

        assert tuple(rgba[0, 0]) == (255, 255, 0, 255)

    def test_grayscale_endpoints(self):
        rgba = ColorRamp("grayscale").render(
            np.array([[0.0, 1.0]]), value_min=0.0, value_max=1.0
        )

        assert tuple(rgba[0, 0]) == (0, 0, 0, 255)
        assert tuple(rgba[0, 1]) == (255, 255, 255, 255)

    def test_viridis_endpoints(self):
        rgba = ColorRamp("viridis").render(
            np.array([[0.0, 1.0]]), value_min=0.0, value_max=1.0
        )

        assert tuple(rgba[0, 0]) == (68, 1, 84, 255)
        assert tuple(rgba[0, 1]) == (253, 231, 37, 255)

    def test_values_outside_range_are_clamped(self):
        rgba = ColorRamp("grayscale").render(
            np.array([[-5.0, 99.0]]), value_min=0.0, value_max=1.0
        )

        assert tuple(rgba[0, 0]) == (0, 0, 0, 255)
        assert tuple(rgba[0, 1]) == (255, 255, 255, 255)


class TestNodata:
    def test_nan_becomes_transparent(self):
        rgba = ColorRamp("grayscale").render(
            np.array([[np.nan, 1.0]]), value_min=0.0, value_max=1.0
        )

        assert rgba[0, 0, 3] == 0
        assert rgba[0, 1, 3] == 255

    def test_infinite_values_become_transparent(self):
        rgba = ColorRamp("grayscale").render(
            np.array([[np.inf, -np.inf]]), value_min=0.0, value_max=1.0
        )

        assert tuple(rgba[0, 0]) == (0, 0, 0, 0)
        assert tuple(rgba[0, 1]) == (0, 0, 0, 0)

    def test_all_nan_band_is_fully_transparent(self):
        rgba = ColorRamp("viridis").render(
            np.full((3, 4), np.nan), value_min=0.0, value_max=1.0
        )

        assert rgba.shape == (3, 4, 4)
        assert (rgba[..., 3] == 0).all()


class TestConstantRange:
    def test_constant_band_renders_mid_ramp_colour(self):
        rgba = ColorRamp("slope").render(
            np.full((2, 2), 7.0), value_min=7.0, value_max=7.0
        )

        assert (rgba == np.array([255, 255, 0, 255], dtype=np.uint8)).all()

    def test_constant_grayscale_midpoint(self):
        rgba = ColorRamp("grayscale").render(
            np.array([[3.0]]), value_min=3.0, value_max=3.0
        )

        assert tuple(rgba[0, 0]) == (128, 128, 128, 255)


class TestValidation:
    def test_unknown_ramp_name_raises(self):
        with pytest.raises(RasterValidationError) as excinfo:
            ColorRamp("jet")

        assert "slope" in str(excinfo.value)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(RasterValidationError):
            ColorRamp("slope").render(
                np.array([[1.0]]), value_min=5.0, value_max=1.0
            )

    def test_non_2d_input_raises(self):
        with pytest.raises(RasterValidationError):
            ColorRamp("slope").render(
                np.array([1.0, 2.0]), value_min=0.0, value_max=2.0
            )

    def test_non_finite_range_raises(self):
        with pytest.raises(RasterValidationError):
            ColorRamp("slope").render(
                np.array([[1.0]]), value_min=np.nan, value_max=2.0
            )
