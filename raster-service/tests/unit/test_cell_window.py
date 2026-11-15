import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.cell_window import CellWindow
from app.core.domain.grid_geometry import GridGeometry
from app.core.errors.exceptions import RasterValidationError

EXTENT = BoundingBox(min_lon=77.0, min_lat=18.0, max_lon=78.0, max_lat=19.0)


@pytest.fixture
def grid() -> GridGeometry:
    return GridGeometry(EXTENT, rows=10, cols=10)


class TestWithHalo:
    def test_interior_halo_expands_on_all_sides(self):
        window = CellWindow.with_halo(
            row_start=3, row_stop=6, col_start=4, col_stop=7,
            halo_cells=1, grid_rows=10, grid_cols=10,
        )

        assert (window.row_start, window.row_stop) == (2, 7)
        assert (window.col_start, window.col_stop) == (3, 8)
        assert (window.core_row_start, window.core_row_stop) == (3, 6)
        assert (window.core_col_start, window.core_col_stop) == (4, 7)
        assert (window.row_off, window.col_off) == (1, 1)
        assert (window.core_rows, window.core_cols) == (3, 3)

    def test_halo_clipped_at_north_west_edge(self):
        window = CellWindow.with_halo(
            row_start=0, row_stop=2, col_start=0, col_stop=2,
            halo_cells=2, grid_rows=10, grid_cols=10,
        )

        assert (window.row_start, window.row_stop) == (0, 4)
        assert (window.col_start, window.col_stop) == (0, 4)
        assert (window.row_off, window.col_off) == (0, 0)

    def test_halo_clipped_at_south_east_edge(self):
        window = CellWindow.with_halo(
            row_start=8, row_stop=10, col_start=8, col_stop=10,
            halo_cells=3, grid_rows=10, grid_cols=10,
        )

        assert (window.row_start, window.row_stop) == (5, 10)
        assert (window.col_start, window.col_stop) == (5, 10)
        assert (window.row_off, window.col_off) == (3, 3)

    def test_zero_halo_keeps_core(self):
        window = CellWindow.with_halo(
            row_start=3, row_stop=6, col_start=4, col_stop=7,
            halo_cells=0, grid_rows=10, grid_cols=10,
        )

        assert (window.row_start, window.row_stop) == (3, 6)
        assert (window.row_off, window.col_off) == (0, 0)

    def test_negative_halo_raises(self):
        with pytest.raises(RasterValidationError):
            CellWindow.with_halo(
                row_start=3, row_stop=6, col_start=4, col_stop=7,
                halo_cells=-1, grid_rows=10, grid_cols=10,
            )


class TestAround:
    def test_centered_window(self):
        window = CellWindow.around(center_row=5, center_col=5, radius_cells=2)

        assert (window.rows, window.cols) == (5, 5)
        assert (window.row_start, window.col_start) == (3, 3)
        # Core equals the whole window on point reads.
        assert (window.row_off, window.col_off) == (0, 0)
        assert (window.core_rows, window.core_cols) == (5, 5)

    def test_window_may_extend_past_grid_edges(self):
        window = CellWindow.around(center_row=0, center_col=0, radius_cells=2)

        assert window.row_start == -2
        assert window.col_start == -2
        assert (window.rows, window.cols) == (5, 5)

    def test_negative_radius_raises(self):
        with pytest.raises(RasterValidationError):
            CellWindow.around(center_row=5, center_col=5, radius_cells=-1)


class TestSlicesAndBounds:
    def test_read_slices_cover_outer_range(self):
        window = CellWindow.with_halo(
            row_start=3, row_stop=6, col_start=4, col_stop=7,
            halo_cells=1, grid_rows=10, grid_cols=10,
        )

        assert window.rows_slice == slice(2, 7)
        assert window.cols_slice == slice(3, 8)

    def test_core_slice_positions_core_inside_output(self):
        window = CellWindow.with_halo(
            row_start=3, row_stop=6, col_start=4, col_stop=7,
            halo_cells=1, grid_rows=10, grid_cols=10,
        )

        assert window.core_slice == (slice(1, 4), slice(1, 4))

    def test_outer_bounds(self, grid: GridGeometry):
        window = CellWindow.with_halo(
            row_start=3, row_stop=6, col_start=4, col_stop=7,
            halo_cells=1, grid_rows=10, grid_cols=10,
        )

        min_lon, min_lat, max_lon, max_lat = window.outer_bounds(grid)

        assert min_lon == pytest.approx(77.3)
        assert max_lon == pytest.approx(77.8)
        assert max_lat == pytest.approx(18.8)
        assert min_lat == pytest.approx(18.3)

    def test_point_window_bounds_may_exceed_extent(
        self, grid: GridGeometry
    ):
        window = CellWindow.around(center_row=0, center_col=0, radius_cells=1)

        min_lon, min_lat, max_lon, max_lat = window.outer_bounds(grid)

        assert max_lat == pytest.approx(19.1)
        assert min_lon == pytest.approx(76.9)

    def test_bounds_beyond_planet_edges_do_not_raise(
        self, grid: GridGeometry
    ):
        # A point+radius read pads out-of-extent cells and must never
        # fail (A3), even when the window crosses the poles/antimeridian.
        window = CellWindow.around(
            center_row=0, center_col=0, radius_cells=3000
        )

        min_lon, min_lat, max_lon, max_lat = window.outer_bounds(grid)

        assert max_lat > 90.0
        assert min_lon < -180.0


class TestValidation:
    def test_core_outside_outer_raises(self):
        with pytest.raises(RasterValidationError):
            CellWindow(
                row_start=1, row_stop=3, col_start=1, col_stop=3,
                core_row_start=0, core_row_stop=3,
                core_col_start=1, core_col_stop=3,
            )

    def test_empty_outer_raises(self):
        with pytest.raises(RasterValidationError):
            CellWindow(
                row_start=2, row_stop=2, col_start=1, col_stop=3,
                core_row_start=2, core_row_stop=3,
                core_col_start=1, core_col_stop=3,
            )

    def test_non_integer_bound_raises(self):
        with pytest.raises(RasterValidationError):
            CellWindow(
                row_start=1.5, row_stop=3, col_start=1, col_stop=3,
                core_row_start=1, core_row_stop=3,
                core_col_start=1, core_col_stop=3,
            )
