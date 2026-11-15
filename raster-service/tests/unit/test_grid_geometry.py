import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.domain.grid_geometry import GridGeometry
from app.core.errors.exceptions import (
    NoCoverageError,
    RasterValidationError,
)

EXTENT = BoundingBox(min_lon=77.0, min_lat=18.0, max_lon=78.0, max_lat=19.0)


@pytest.fixture
def grid() -> GridGeometry:
    # 10x10 grid over a 1x1 degree extent -> 0.1 degree cells.
    return GridGeometry(EXTENT, rows=10, cols=10)


class TestConstruction:
    @pytest.mark.parametrize(("rows", "cols"), [(0, 10), (10, -1), (1.5, 10), ("5", 5)])
    def test_invalid_shape_raises(self, rows, cols):
        with pytest.raises(RasterValidationError):
            GridGeometry(EXTENT, rows=rows, cols=cols)

    def test_exposes_extent(self, grid: GridGeometry) -> None:
        assert grid.extent == EXTENT
        assert grid.rows == 10
        assert grid.cols == 10


class TestResolution:
    def test_resolution_properties(self, grid: GridGeometry) -> None:
        assert grid.res_lon_deg == pytest.approx(0.1)
        assert grid.res_lat_deg == pytest.approx(0.1)

    def test_row_center_lat(self, grid: GridGeometry) -> None:
        assert grid.row_center_lat(0) == pytest.approx(18.95)
        assert grid.row_center_lat(9) == pytest.approx(18.05)

    def test_rows_mean_lat(self, grid: GridGeometry) -> None:
        assert grid.rows_mean_lat(0, 10) == pytest.approx(18.5)


class TestCellAt:
    def test_cell_centres(self, grid: GridGeometry) -> None:
        assert grid.cell_at(GeoPoint(lat=18.95, lon=77.05)) == (0, 0)
        assert grid.cell_at(GeoPoint(lat=18.05, lon=77.95)) == (9, 9)

    @pytest.mark.parametrize(
        "lat, lon, expected",
        [
            (19.0, 77.0, (0, 0)),
            (19.0, 78.0, (0, 9)),
            (18.0, 77.0, (9, 0)),
            (18.0, 78.0, (9, 9)),
        ],
    )
    def test_exact_edges_and_corners(
        self, grid: GridGeometry, lat: float, lon: float, expected
    ) -> None:
        assert grid.cell_at(GeoPoint(lat=lat, lon=lon)) == expected

    def test_outside_extent_returns_none(self, grid: GridGeometry) -> None:
        assert grid.cell_at(GeoPoint(lat=19.1, lon=77.5)) is None
        assert grid.cell_at(GeoPoint(lat=18.5, lon=76.9)) is None


class TestWindowForBbox:
    def test_cells_with_centres_inside(self, grid: GridGeometry) -> None:
        # Cell centres inside: lon 77.15/77.25/77.35, lat 18.15/18.25/18.35.
        bounds = grid.window_for_bbox(
            BoundingBox(min_lon=77.11, min_lat=18.11, max_lon=77.39, max_lat=18.39),
            max_cells=100,
        )
        assert bounds == (6, 9, 1, 4)

    def test_centre_exactly_on_bbox_edge_counts_inside(
        self, grid: GridGeometry
    ) -> None:
        # Cell centre lat 18.95 / lon 77.05 sit exactly on the bbox max
        # edges; the index epsilon must keep those cells selected.
        bounds = grid.window_for_bbox(
            BoundingBox(
                min_lon=77.0, min_lat=18.0, max_lon=77.05, max_lat=18.95
            ),
            max_cells=100,
        )
        assert bounds == (0, 10, 0, 1)

    def test_non_intersecting_raises(self, grid: GridGeometry) -> None:
        with pytest.raises(NoCoverageError):
            grid.window_for_bbox(
                BoundingBox(min_lon=70.0, min_lat=10.0, max_lon=71.0, max_lat=11.0),
                max_cells=100,
            )

    def test_zero_cells_falls_back_to_single_cell(
        self, grid: GridGeometry
    ) -> None:
        # Bbox smaller than one cell: no cell centre inside -> the single
        # cell containing the intersection centre is returned.
        bounds = grid.window_for_bbox(
            BoundingBox(
                min_lon=77.141, min_lat=18.941, max_lon=77.149, max_lat=18.949
            ),
            max_cells=100,
        )
        assert bounds == (0, 1, 1, 2)

    def test_max_cells_exceeded_raises(self, grid: GridGeometry) -> None:
        with pytest.raises(RasterValidationError):
            grid.window_for_bbox(
                BoundingBox(
                    min_lon=77.11, min_lat=18.11, max_lon=77.39, max_lat=18.39
                ),
                max_cells=4,  # the window holds 9 cells
            )


class TestPaddedSlices:
    def test_interior_window_no_padding(self, grid: GridGeometry) -> None:
        src_r, src_c, dst_r, dst_c = grid.padded_slices(5, 5, 2)
        assert (src_r.start, src_r.stop) == (3, 8)
        assert (src_c.start, src_c.stop) == (3, 8)
        assert (dst_r.start, dst_r.stop) == (0, 5)
        assert (dst_c.start, dst_c.stop) == (0, 5)

    def test_corner_window_is_padded(self, grid: GridGeometry) -> None:
        src_r, src_c, dst_r, dst_c = grid.padded_slices(0, 0, 1)
        assert (src_r.start, src_r.stop) == (0, 2)
        assert (src_c.start, src_c.stop) == (0, 2)
        assert (dst_r.start, dst_r.stop) == (1, 3)
        assert (dst_c.start, dst_c.stop) == (1, 3)

    def test_far_edge_window_is_padded(self, grid: GridGeometry) -> None:
        src_r, src_c, dst_r, dst_c = grid.padded_slices(9, 9, 1)
        assert (src_r.start, src_r.stop) == (8, 10)
        assert (src_c.start, src_c.stop) == (8, 10)
        assert (dst_r.start, dst_r.stop) == (0, 2)
        assert (dst_c.start, dst_c.stop) == (0, 2)


class TestWindowSize:
    def test_valid_radius(self, grid: GridGeometry) -> None:
        assert grid.window_size(0) == 1
        assert grid.window_size(2) == 5

    def test_negative_radius_raises(self, grid: GridGeometry) -> None:
        with pytest.raises(RasterValidationError):
            grid.window_size(-1)

    def test_non_integer_radius_raises(self, grid: GridGeometry) -> None:
        with pytest.raises(RasterValidationError):
            grid.window_size(1.5)
