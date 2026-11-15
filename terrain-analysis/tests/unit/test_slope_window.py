import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.domain.slope_window import SlopeWindow
from app.core.errors.exceptions import DomainValidationError
from app.core.ports.terrain_repository import TerrainRepository
from app.features.area_analysis.domain.area_stats import AreaStats
from app.features.area_analysis.domain.value_stats import ValueStats


def make_window(slope_deg=None, cell_size_x_m=90.0, cell_size_y_m=90.0):
    if slope_deg is None:
        slope_deg = np.zeros((3, 3))
    return SlopeWindow(
        slope_deg=slope_deg,
        cell_size_x_m=cell_size_x_m,
        cell_size_y_m=cell_size_y_m,
    )


class TestSlopeWindowValidation:
    def test_valid_window(self):
        window = make_window()

        assert window.slope_deg.shape == (3, 3)
        assert window.slope_deg.dtype == np.float64
        assert window.cell_size_x_m == 90.0
        assert window.cell_size_y_m == 90.0

    def test_accepts_array_like_and_coerces_to_float64(self):
        window = make_window(slope_deg=[[1, 2], [3, 4]])

        assert window.slope_deg.dtype == np.float64
        assert window.slope_deg.shape == (2, 2)

    @pytest.mark.parametrize(
        "slope_deg",
        [
            np.zeros(5),
            np.zeros((2, 2, 2)),
            np.zeros((0, 0)),
            np.zeros((3, 0)),
        ],
    )
    def test_non_2d_or_empty_raises(self, slope_deg):
        with pytest.raises(DomainValidationError):
            make_window(slope_deg=slope_deg)

    @pytest.mark.parametrize("bad_size", [0.0, -1.0, np.nan, np.inf])
    def test_invalid_cell_size_raises(self, bad_size):
        with pytest.raises(DomainValidationError):
            make_window(cell_size_x_m=bad_size)
        with pytest.raises(DomainValidationError):
            make_window(cell_size_y_m=bad_size)


class TestSlopeWindowHelpers:
    def test_center_value(self):
        window = make_window(slope_deg=np.arange(9).reshape(3, 3))

        assert window.center_value() == 4.0

    def test_center_value_nan(self):
        slope_deg = np.arange(9, dtype=np.float64).reshape(3, 3)
        slope_deg[1, 1] = np.nan

        assert np.isnan(make_window(slope_deg=slope_deg).center_value())

    def test_valid_values_returns_finite_cells(self):
        slope_deg = np.array(
            [[1.0, np.nan, 3.0], [np.inf, 5.0, np.nan], [7.0, 8.0, 9.0]]
        )
        window = make_window(slope_deg=slope_deg)

        np.testing.assert_array_equal(
            window.valid_values(), np.array([1.0, 3.0, 5.0, 7.0, 8.0, 9.0])
        )

    def test_valid_values_empty_when_all_nodata(self):
        window = make_window(slope_deg=np.full((3, 3), np.nan))

        assert window.valid_values().shape == (0,)

    def test_is_all_nodata_true_when_every_cell_nan(self):
        window = make_window(slope_deg=np.full((3, 3), np.nan))

        assert window.is_all_nodata() is True

    def test_is_all_nodata_false_with_any_valid_cell(self):
        slope_deg = np.full((3, 3), np.nan)
        slope_deg[0, 0] = 12.5

        assert make_window(slope_deg=slope_deg).is_all_nodata() is False


class _MinimalRepository(TerrainRepository):
    def elevation_at(self, point: GeoPoint) -> float:
        return 0.0

    def window_around(self, point: GeoPoint, radius_cells: int = 1) -> DemWindow:
        raise NotImplementedError

    def window_for(self, bbox: BoundingBox) -> DemWindow:
        raise NotImplementedError

    def window_for_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


class TestTerrainRepositorySlopeDefaults:
    def test_provides_slope_defaults_to_false(self):
        assert _MinimalRepository().provides_slope() is False

    def test_slope_window_around_defaults_to_not_implemented(self):
        with pytest.raises(NotImplementedError):
            _MinimalRepository().slope_window_around(
                GeoPoint(lat=18.5, lon=77.5)
            )

    def test_slope_window_for_defaults_to_not_implemented(self):
        with pytest.raises(NotImplementedError):
            _MinimalRepository().slope_window_for(
                BoundingBox(
                    min_lon=77.4, min_lat=18.4, max_lon=77.6, max_lat=18.6
                )
            )


class TestAreaStatsOptionalElevation:
    def test_elevation_m_accepts_none(self):
        stats = AreaStats(
            elevation_m=None,
            slope_deg=ValueStats(min=1.0, max=5.0, mean=3.0),
            steep_fraction=0.25,
        )

        assert stats.elevation_m is None
        assert stats.slope_deg.mean == 3.0
