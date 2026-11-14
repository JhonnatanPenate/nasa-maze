import math

import numpy as np
import pytest

from app.core.domain.dem_window import DemWindow
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_class import TerrainClass
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.errors.exceptions import NoCoverageError

CELL = 30.0


def x_gradient_window(angle_deg: float, cell_x=CELL, cell_y=CELL, rows=5, cols=5) -> DemWindow:
    column = np.arange(cols) * cell_x * math.tan(math.radians(angle_deg))
    elevation = np.tile(column, (rows, 1))
    return DemWindow(elevation=elevation, cell_size_x_m=cell_x, cell_size_y_m=cell_y)


def y_gradient_window(angle_deg: float, cell_x=CELL, cell_y=CELL, rows=6, cols=4) -> DemWindow:
    row = np.arange(rows)[:, None] * cell_y * math.tan(math.radians(angle_deg))
    elevation = np.tile(row, (1, cols))
    return DemWindow(elevation=elevation, cell_size_x_m=cell_x, cell_size_y_m=cell_y)


def diagonal_gradient_window(angle_deg: float, cell=CELL, rows=5, cols=5) -> DemWindow:
    # Plane tilted along both axes: dz_dx = dz_dy = tan(angle)/sqrt(2),
    # so the combined slope magnitude is exactly angle_deg.
    m = math.tan(math.radians(angle_deg)) / math.sqrt(2.0)
    j, k = np.mgrid[0:rows, 0:cols]
    return DemWindow(
        elevation=(j + k) * cell * m, cell_size_x_m=cell, cell_size_y_m=cell
    )


CORNER_MASK_5x5 = np.array(
    [
        [False, True, True, True, False],
        [True, True, True, True, True],
        [True, True, True, True, True],
        [True, True, True, True, True],
        [False, True, True, True, False],
    ]
)


class TestCompute:
    def test_x_gradient_exact_on_all_cells_except_corners(self):
        slope = SlopeCalculator().compute(x_gradient_window(10.0))

        np.testing.assert_allclose(slope[CORNER_MASK_5x5], 10.0, rtol=1e-9)
        # At array corners one mirrored diagonal neighbour pair is mutually
        # out of bounds, so both fall back to the centre value. For an
        # x-gradient on square cells that yields dz_dx = 0.75*a, dz_dy = 0.25*a.
        expected_corner = math.degrees(
            math.atan(math.tan(math.radians(10.0)) * math.sqrt(0.625))
        )
        np.testing.assert_allclose(
            slope[~CORNER_MASK_5x5], expected_corner, rtol=1e-9
        )

    def test_y_gradient_exact_on_all_cells_except_corners(self):
        slope = SlopeCalculator().compute(y_gradient_window(20.0))

        mask = np.ones((6, 4), dtype=bool)
        mask[0, 0] = mask[0, -1] = mask[-1, 0] = mask[-1, -1] = False
        np.testing.assert_allclose(slope[mask], 20.0, rtol=1e-9)
        assert np.isfinite(slope).all()

    def test_diagonal_plane_exact_except_opposite_missing_corners(self):
        slope = SlopeCalculator().compute(diagonal_gradient_window(10.0))

        exact = np.ones((5, 5), dtype=bool)
        exact[0, -1] = False
        exact[-1, 0] = False
        np.testing.assert_allclose(slope[exact], 10.0, rtol=1e-9)
        # On the anti-diagonal corners the mutually-missing pair does not
        # match the plane direction; fallback gives atan(tan(a)/2).
        expected = math.degrees(math.atan(math.tan(math.radians(10.0)) / 2.0))
        np.testing.assert_allclose(slope[~exact], expected, rtol=1e-9)

    def test_flat_plane_gives_zero_slope(self):
        window = DemWindow(
            elevation=np.full((4, 4), 500.0), cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        np.testing.assert_array_equal(
            SlopeCalculator().compute(window), np.zeros((4, 4))
        )

    def test_anisotropic_cell_sizes_respected(self):
        slope = SlopeCalculator().compute(
            x_gradient_window(10.0, cell_x=30.0, cell_y=7.5)
        )

        np.testing.assert_allclose(slope[CORNER_MASK_5x5], 10.0, rtol=1e-9)

    def test_nan_neighbour_does_not_attenuate_planar_slope(self):
        elevation = x_gradient_window(10.0).elevation
        elevation[2, 2] = np.nan
        window = DemWindow(
            elevation=elevation, cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        slope = SlopeCalculator().compute(window)

        assert np.isnan(slope[2, 2])
        assert int(np.isnan(slope).sum()) == 1
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                assert slope[2 + dr, 2 + dc] == pytest.approx(10.0, rel=1e-9)

    def test_cell_with_all_neighbours_nan_gives_nan_slope(self):
        elevation = np.full((3, 3), np.nan)
        elevation[1, 1] = 100.0
        window = DemWindow(
            elevation=elevation, cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        slope = SlopeCalculator().compute(window)

        assert np.isnan(slope[1, 1])

    def test_slope_next_to_nodata_edge_not_attenuated(self):
        # 5x5 window: NaN north row and west column around a valid 3x3
        # carrying a 31-degree planar gradient along x.
        j, k = np.mgrid[0:5, 0:5]
        elevation = np.full((5, 5), np.nan)
        elevation[1:4, 1:4] = k[1:4, 1:4] * CELL * math.tan(math.radians(31.0))
        window = DemWindow(
            elevation=elevation, cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        slope = SlopeCalculator().compute(window)

        assert slope[2, 2] == pytest.approx(31.0, rel=1e-9)
        for pos in ((1, 2), (2, 1), (2, 3), (3, 2)):
            assert slope[pos] == pytest.approx(31.0, rel=1e-9)
        assert (
            TerrainClassifier().classify(float(slope[2, 2]))
            == TerrainClass.HAZARDOUS
        )

    def test_single_cell_window_gives_nan_slope(self):
        window = DemWindow(
            elevation=np.array([[42.0]]), cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        assert np.isnan(SlopeCalculator().compute(window)[0, 0])

    def test_all_nodata_raises_no_coverage(self):
        window = DemWindow(
            elevation=np.full((3, 3), np.nan),
            cell_size_x_m=CELL,
            cell_size_y_m=CELL,
        )

        with pytest.raises(NoCoverageError):
            SlopeCalculator().compute(window)


class TestComputeAtCenter:
    def test_returns_center_slope(self):
        slope = SlopeCalculator().compute_at_center(x_gradient_window(10.0))

        assert isinstance(slope, float)
        assert slope == pytest.approx(10.0, rel=1e-9)

    def test_nan_center_raises_no_coverage(self):
        elevation = np.arange(9, dtype=np.float64).reshape(3, 3)
        elevation[1, 1] = np.nan
        window = DemWindow(
            elevation=elevation, cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        with pytest.raises(NoCoverageError):
            SlopeCalculator().compute_at_center(window)

    def test_valid_center_with_all_neighbours_nan_raises_no_coverage(self):
        elevation = np.full((3, 3), np.nan)
        elevation[1, 1] = 100.0
        window = DemWindow(
            elevation=elevation, cell_size_x_m=CELL, cell_size_y_m=CELL
        )

        with pytest.raises(NoCoverageError):
            SlopeCalculator().compute_at_center(window)

    def test_all_nodata_raises_no_coverage(self):
        window = DemWindow(
            elevation=np.full((3, 3), np.nan),
            cell_size_x_m=CELL,
            cell_size_y_m=CELL,
        )

        with pytest.raises(NoCoverageError):
            SlopeCalculator().compute_at_center(window)
