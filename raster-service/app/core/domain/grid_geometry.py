import math

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    NoCoverageError,
    RasterValidationError,
)

# Tolerance (in cell-index units) so a cell centre lying exactly on a bbox
# edge still counts as inside despite floating-point error.
_INDEX_EPS = 1e-9


class GridGeometry:
    """Pixel/geo index math for a north-up regular lon/lat grid.

    Row 0 holds the northernmost cells (max_lat edge), column 0 the
    westernmost cells (min_lon edge). Cell (row, col) centres are spaced
    res_lat_deg/res_lon_deg apart. Cell selection semantics are identical
    to MS4's GridGeometry (HTTP contract parity).
    """

    def __init__(self, extent: BoundingBox, rows: int, cols: int) -> None:
        if not isinstance(rows, int) or not isinstance(cols, int) or rows < 1 or cols < 1:
            raise RasterValidationError(
                f"GridGeometry needs positive int rows/cols, got {rows}x{cols}"
            )
        self._extent = extent
        self._rows = rows
        self._cols = cols
        self._res_lon_deg = (extent.max_lon - extent.min_lon) / cols
        self._res_lat_deg = (extent.max_lat - extent.min_lat) / rows

    @property
    def extent(self) -> BoundingBox:
        return self._extent

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def res_lon_deg(self) -> float:
        return self._res_lon_deg

    @property
    def res_lat_deg(self) -> float:
        return self._res_lat_deg

    def intersects(self, bbox: BoundingBox) -> bool:
        e = self._extent
        return not (
            bbox.max_lon < e.min_lon
            or bbox.min_lon > e.max_lon
            or bbox.max_lat < e.min_lat
            or bbox.min_lat > e.max_lat
        )

    def cell_at(self, point: GeoPoint) -> tuple[int, int] | None:
        """(row, col) of the cell containing point, or None when point lies
        outside the extent. Points exactly on a max edge are clamped into
        the boundary cell (floor gives index == size there)."""
        if not self._extent.contains(point):
            return None
        e = self._extent
        row = int(math.floor((e.max_lat - point.lat) / self._res_lat_deg))
        col = int(math.floor((point.lon - e.min_lon) / self._res_lon_deg))
        row = min(max(row, 0), self._rows - 1)
        col = min(max(col, 0), self._cols - 1)
        return row, col

    def cell_bounds_for_bbox(
        self, bbox: BoundingBox
    ) -> tuple[int, int, int, int]:
        """(row_start, row_stop, col_start, col_stop) of cells whose centres
        fall inside bbox, clipped to the grid. May describe an empty range."""
        e = self._extent
        col_start = math.ceil(
            (bbox.min_lon - e.min_lon) / self._res_lon_deg - 0.5 - _INDEX_EPS
        )
        col_stop = (
            math.floor(
                (bbox.max_lon - e.min_lon) / self._res_lon_deg - 0.5 + _INDEX_EPS
            )
            + 1
        )
        row_start = math.ceil(
            (e.max_lat - bbox.max_lat) / self._res_lat_deg - 0.5 - _INDEX_EPS
        )
        row_stop = (
            math.floor(
                (e.max_lat - bbox.min_lat) / self._res_lat_deg - 0.5 + _INDEX_EPS
            )
            + 1
        )
        return (
            min(max(row_start, 0), self._rows),
            min(max(row_stop, 0), self._rows),
            min(max(col_start, 0), self._cols),
            min(max(col_stop, 0), self._cols),
        )

    def window_for_bbox(
        self, bbox: BoundingBox, max_cells: int
    ) -> tuple[int, int, int, int]:
        """Clipped (row_start, row_stop, col_start, col_stop) for bbox.

        Raises NoCoverageError when bbox does not intersect the extent and
        RasterValidationError when the window would exceed max_cells. A bbox
        covering no cell centre falls back to the single cell containing the
        intersection centre."""
        if not self.intersects(bbox):
            raise NoCoverageError(
                f"Bounding box {bbox} does not intersect the grid extent "
                f"{self._extent}"
            )
        row_start, row_stop, col_start, col_stop = self.cell_bounds_for_bbox(
            bbox
        )
        if row_stop <= row_start or col_stop <= col_start:
            centre = self._intersection_centre(bbox)
            cell = self.cell_at(centre)
            if cell is None:  # pragma: no cover - intersects() guarantees it
                raise NoCoverageError(
                    f"Bounding box {bbox} does not intersect the grid extent"
                )
            row_start, row_stop = cell[0], cell[0] + 1
            col_start, col_stop = cell[1], cell[1] + 1
        cells = (row_stop - row_start) * (col_stop - col_start)
        if cells > max_cells:
            raise RasterValidationError(
                f"Requested window holds {cells} cells, exceeding the limit "
                f"of {max_cells}"
            )
        return row_start, row_stop, col_start, col_stop

    def padded_slices(
        self, center_row: int, center_col: int, radius_cells: int
    ) -> tuple[slice, slice, slice, slice]:
        """(src_row, src_col, dst_row, dst_col) slices copying the in-extent
        part of a (2*radius+1)^2 window centred on (center_row, center_col)
        into a full-size output array; the rest stays NaN padding."""
        self.window_size(radius_cells)  # validates radius_cells
        row_start = max(center_row - radius_cells, 0)
        row_stop = min(center_row + radius_cells + 1, self._rows)
        col_start = max(center_col - radius_cells, 0)
        col_stop = min(center_col + radius_cells + 1, self._cols)
        dst_row_start = row_start - (center_row - radius_cells)
        dst_col_start = col_start - (center_col - radius_cells)
        return (
            slice(row_start, row_stop),
            slice(col_start, col_stop),
            slice(dst_row_start, dst_row_start + (row_stop - row_start)),
            slice(dst_col_start, dst_col_start + (col_stop - col_start)),
        )

    @staticmethod
    def window_size(radius_cells: int) -> int:
        if (
            isinstance(radius_cells, bool)
            or not isinstance(radius_cells, int)
            or radius_cells < 0
        ):
            raise RasterValidationError(
                f"radius_cells must be an integer >= 0, got {radius_cells!r}"
            )
        return 2 * radius_cells + 1

    def row_center_lat(self, row: int) -> float:
        return self._extent.max_lat - (row + 0.5) * self._res_lat_deg

    def rows_mean_lat(self, row_start: int, row_stop: int) -> float:
        return (
            self._extent.max_lat
            - (row_start + row_stop) / 2.0 * self._res_lat_deg
        )

    def _intersection_centre(self, bbox: BoundingBox) -> GeoPoint:
        e = self._extent
        return GeoPoint(
            lat=(
                max(bbox.min_lat, e.min_lat) + min(bbox.max_lat, e.max_lat)
            )
            / 2.0,
            lon=(
                max(bbox.min_lon, e.min_lon) + min(bbox.max_lon, e.max_lon)
            )
            / 2.0,
        )
