import numpy as np

from app.core.domain.cell_window import CellWindow
from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.domain.grid_geometry import GridGeometry
from app.core.errors.exceptions import RasterValidationError
from app.core.ports.raster_repository import RasterRepository
from app.features.window_read.domain.window_request import WindowRequest


class ReadWindow:
    """`POST /raster/{dataset}/window` — cell window read (plan F4).

    Reproduces MS4 `GridBackedRasterDatasource` semantics bit-for-bit:
    bbox reads select the cells whose centres fall inside (with the
    single-cell fallback), the cell cap applies to core cells before
    any read, and point+radius reads pad out-of-extent cells with NaN
    instead of failing.
    """

    def __init__(
        self, repository: RasterRepository, max_window_cells: int
    ) -> None:
        self._repository = repository
        self._max_window_cells = max_window_cells

    def execute(
        self, dataset: str, request: WindowRequest
    ) -> tuple[DatasetMetadata, CellWindow, np.ndarray, float]:
        """(metadata, window, cells, center_lat_deg).

        `cells` holds the outer window (halo included, NaN for nodata
        and for out-of-extent padding). `center_lat` is the core rows'
        mean latitude on bbox reads and the containing cell's
        row-centre latitude on point reads — the request latitude when
        the point lies outside the extent.
        """
        metadata = self._repository.metadata(dataset)
        band = metadata.band(request.band).name
        geometry = metadata.grid_geometry()
        if request.point is not None:
            window, cells, center_lat = self._point_window(
                dataset, request, band, geometry
            )
        else:
            window, cells, center_lat = self._bbox_window(
                dataset, request, band, geometry
            )
        return metadata, window, cells, center_lat

    def _bbox_window(
        self,
        dataset: str,
        request: WindowRequest,
        band: str,
        geometry: GridGeometry,
    ) -> tuple[CellWindow, np.ndarray, float]:
        # window_for_bbox raises NoCoverageError when the bbox misses
        # the extent and RasterValidationError when the core cell count
        # exceeds the cap — both before any cell read.
        row_start, row_stop, col_start, col_stop = (
            geometry.window_for_bbox(request.bbox, self._max_window_cells)
        )
        window = CellWindow.with_halo(
            row_start,
            row_stop,
            col_start,
            col_stop,
            request.halo_cells,
            geometry.rows,
            geometry.cols,
        )
        cells = self._repository.read_cells(
            dataset, band, window.rows_slice, window.cols_slice
        )
        # The core rows' mean latitude matches MS4 even when the halo
        # was clipped asymmetrically at the grid edge.
        center_lat = geometry.rows_mean_lat(row_start, row_stop)
        return window, cells, center_lat

    def _point_window(
        self,
        dataset: str,
        request: WindowRequest,
        band: str,
        geometry: GridGeometry,
    ) -> tuple[CellWindow, np.ndarray, float]:
        size = GridGeometry.window_size(request.radius_cells)
        if size * size > self._max_window_cells:
            raise RasterValidationError(
                f"Requested {size}x{size} window ({size * size} cells) "
                f"exceeds the limit of {self._max_window_cells}"
            )
        cell = geometry.cell_at(request.point)
        cells = np.full((size, size), np.nan)
        if cell is None:
            # Point reads never fail for coverage: the window anchors on
            # the unbounded-grid index of the point and stays all-NaN.
            anchor_row, anchor_col = geometry.unbounded_cell_at(
                request.point
            )
            window = CellWindow.around(
                anchor_row, anchor_col, request.radius_cells
            )
            center_lat = request.point.lat
        else:
            window = CellWindow.around(
                cell[0], cell[1], request.radius_cells
            )
            src_rows, src_cols, dst_rows, dst_cols = (
                geometry.padded_slices(
                    cell[0], cell[1], request.radius_cells
                )
            )
            cells[dst_rows, dst_cols] = self._repository.read_cells(
                dataset, band, src_rows, src_cols
            )
            center_lat = geometry.row_center_lat(cell[0])
        return window, cells, center_lat
