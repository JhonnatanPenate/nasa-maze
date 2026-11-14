from abc import abstractmethod

import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.errors.exceptions import DomainValidationError
from app.core.ports.raster_datasource import RasterDatasource
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.grid_geometry import GridGeometry


class GridBackedRasterDatasource(RasterDatasource):
    """Template-method base for datasources backed by a regular north-up
    lon/lat grid.

    Subclasses provide only I/O: `_geometry()` returns the GridGeometry of
    the backing raster and `_read(row_slice, col_slice)` returns raw
    elevation values plus the nodata sentinel. All index math, window
    capping, and padding live here via GridGeometry.
    """

    def __init__(
        self, mapper: DemWindowMapper, max_window_cells: int
    ) -> None:
        self._mapper = mapper
        self._max_window_cells = max_window_cells

    @abstractmethod
    def _geometry(self) -> GridGeometry:
        """Grid geometry of the backing raster (may open the source)."""

    @abstractmethod
    def _read(
        self, row_slice: slice, col_slice: slice
    ) -> tuple[np.ndarray, float | None]:
        """Raw elevation values for the cell range plus the nodata sentinel
        (or None). Never called with out-of-grid slices."""

    def read_window(
        self, bbox: BoundingBox, halo_cells: int = 0
    ) -> DemWindow:
        return self.read_window_with_halo(bbox, halo_cells).window

    def read_window_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        if (
            isinstance(halo_cells, bool)
            or not isinstance(halo_cells, int)
            or halo_cells < 0
        ):
            raise DomainValidationError(
                f"halo_cells must be an integer >= 0, got {halo_cells!r}"
            )
        grid = self._geometry()
        # The cap applies to the core cell count; the halo is read on top.
        row_start, row_stop, col_start, col_stop = grid.window_for_bbox(
            bbox, self._max_window_cells
        )
        halo_row_start = max(row_start - halo_cells, 0)
        halo_row_stop = min(row_stop + halo_cells, grid.rows)
        halo_col_start = max(col_start - halo_cells, 0)
        halo_col_stop = min(col_stop + halo_cells, grid.cols)
        raw, nodata = self._read(
            slice(halo_row_start, halo_row_stop),
            slice(halo_col_start, halo_col_stop),
        )
        window = self._mapper.to_dem_window(
            raw,
            nodata,
            grid.res_lon_deg,
            grid.res_lat_deg,
            grid.rows_mean_lat(halo_row_start, halo_row_stop),
        )
        return HaloWindow(
            window=window,
            core_rows=slice(
                row_start - halo_row_start, row_stop - halo_row_start
            ),
            core_cols=slice(
                col_start - halo_col_start, col_stop - halo_col_start
            ),
        )

    def read_window_around(
        self, point: GeoPoint, radius_cells: int
    ) -> DemWindow:
        size = GridGeometry.window_size(radius_cells)
        if size * size > self._max_window_cells:
            raise DomainValidationError(
                f"Requested {size}x{size} window ({size * size} cells) "
                f"exceeds the limit of {self._max_window_cells}"
            )
        grid = self._geometry()
        cell = grid.cell_at(point)
        out = np.full((size, size), np.nan)
        nodata = None
        center_lat = point.lat
        if cell is not None:
            src_r, src_c, dst_r, dst_c = grid.padded_slices(
                cell[0], cell[1], radius_cells
            )
            raw, nodata = self._read(src_r, src_c)
            out[dst_r, dst_c] = raw
            center_lat = grid.row_center_lat(cell[0])
        return self._mapper.to_dem_window(
            out,
            nodata,
            grid.res_lon_deg,
            grid.res_lat_deg,
            center_lat,
        )
