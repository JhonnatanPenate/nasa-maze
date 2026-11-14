import numpy as np
import pytest

from app.core.domain.dem_window import DemWindow
from app.core.errors.exceptions import DomainValidationError


def make_window(elevation=None, cell_size_x_m=30.0, cell_size_y_m=30.0) -> DemWindow:
    if elevation is None:
        elevation = np.zeros((3, 3))
    return DemWindow(
        elevation=elevation,
        cell_size_x_m=cell_size_x_m,
        cell_size_y_m=cell_size_y_m,
    )


class TestDemWindowValidation:
    def test_valid_window(self):
        window = make_window()

        assert window.elevation.shape == (3, 3)
        assert window.elevation.dtype == np.float64
        assert window.cell_size_x_m == 30.0
        assert window.cell_size_y_m == 30.0

    def test_accepts_array_like_and_coerces_to_float64(self):
        window = make_window(elevation=[[1, 2], [3, 4]])

        assert window.elevation.dtype == np.float64
        assert window.elevation.shape == (2, 2)

    @pytest.mark.parametrize(
        "elevation",
        [
            np.zeros(5),          # 1-D
            np.zeros((2, 2, 2)),  # 3-D
            np.zeros((0, 0)),     # empty
            np.zeros((3, 0)),     # empty axis
        ],
    )
    def test_non_2d_or_empty_raises(self, elevation):
        with pytest.raises(DomainValidationError):
            make_window(elevation=elevation)

    @pytest.mark.parametrize("bad_size", [0.0, -1.0, np.nan, np.inf])
    def test_invalid_cell_size_raises(self, bad_size):
        with pytest.raises(DomainValidationError):
            make_window(cell_size_x_m=bad_size)
        with pytest.raises(DomainValidationError):
            make_window(cell_size_y_m=bad_size)


class TestDemWindowHelpers:
    def test_is_all_nodata_true_when_every_cell_nan(self):
        window = make_window(elevation=np.full((3, 3), np.nan))

        assert window.is_all_nodata() is True

    def test_is_all_nodata_false_with_any_valid_cell(self):
        elevation = np.full((3, 3), np.nan)
        elevation[0, 0] = 100.0

        assert make_window(elevation=elevation).is_all_nodata() is False

    def test_center_value_odd_shape(self):
        window = make_window(elevation=np.arange(9).reshape(3, 3))

        assert window.center_value() == 4.0

    def test_center_value_even_shape(self):
        window = make_window(elevation=np.arange(16).reshape(4, 4))

        assert window.center_value() == 10.0  # rows//2=2, cols//2=2

    def test_center_value_nan(self):
        elevation = np.arange(9, dtype=np.float64).reshape(3, 3)
        elevation[1, 1] = np.nan

        assert np.isnan(make_window(elevation=elevation).center_value())
