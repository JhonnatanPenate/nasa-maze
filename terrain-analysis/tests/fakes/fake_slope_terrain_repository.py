import math

import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.dem_window import DemWindow
from app.core.domain.geo_point import GeoPoint
from app.core.domain.halo_window import HaloWindow
from app.core.domain.slope_window import SlopeWindow
from app.core.errors.exceptions import NoCoverageError
from app.core.ports.terrain_repository import TerrainRepository


class FakeSlopeTerrainRepository(TerrainRepository):
    """Grid-mode TerrainRepository stub.

    Serves pre-computed slope windows from a small in-memory array over a
    geographic extent; cells outside the extent read as NaN. DEM reads
    are unsupported and raise NotImplementedError.
    """

    def __init__(
        self,
        slope_deg: np.ndarray,
        extent: BoundingBox,
        cell_size_x_m: float = 90.0,
        cell_size_y_m: float = 90.0,
    ) -> None:
        self._slope_deg = np.asarray(slope_deg, dtype=np.float64)
        self._extent = extent
        self._cell_size_x_m = cell_size_x_m
        self._cell_size_y_m = cell_size_y_m

    def provides_slope(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def elevation_at(self, point: GeoPoint) -> float:
        raise NotImplementedError("grid mode provides no elevation")

    def window_around(
        self, point: GeoPoint, radius_cells: int = 1
    ) -> DemWindow:
        raise NotImplementedError("grid mode provides no DEM windows")

    def window_for(self, bbox: BoundingBox) -> DemWindow:
        raise NotImplementedError("grid mode provides no DEM windows")

    def window_for_with_halo(
        self, bbox: BoundingBox, halo_cells: int
    ) -> HaloWindow:
        raise NotImplementedError("grid mode provides no DEM windows")

    def slope_window_around(
        self, point: GeoPoint, radius_cells: int = 0
    ) -> SlopeWindow:
        row, col = self._cell_of(point)
        return self._extract(
            row - radius_cells,
            row + radius_cells + 1,
            col - radius_cells,
            col + radius_cells + 1,
        )

    def slope_window_for(self, bbox: BoundingBox) -> SlopeWindow:
        if not self._intersects(bbox):
            raise NoCoverageError(
                "Bounding box does not intersect the slope grid extent"
            )
        rows, cols = self._slope_deg.shape
        lon_span = self._extent.max_lon - self._extent.min_lon
        lat_span = self._extent.max_lat - self._extent.min_lat
        col0 = math.floor(
            (bbox.min_lon - self._extent.min_lon) / lon_span * cols
        )
        col1 = math.floor(
            (bbox.max_lon - self._extent.min_lon) / lon_span * cols
        )
        row0 = math.floor(
            (self._extent.max_lat - bbox.max_lat) / lat_span * rows
        )
        row1 = math.floor(
            (self._extent.max_lat - bbox.min_lat) / lat_span * rows
        )
        col0 = min(max(col0, 0), cols - 1)
        col1 = min(max(col1, 0), cols - 1)
        row0 = min(max(row0, 0), rows - 1)
        row1 = min(max(row1, 0), rows - 1)
        return self._extract(row0, row1 + 1, col0, col1 + 1)

    def _intersects(self, bbox: BoundingBox) -> bool:
        return (
            bbox.min_lon < self._extent.max_lon
            and bbox.max_lon > self._extent.min_lon
            and bbox.min_lat < self._extent.max_lat
            and bbox.max_lat > self._extent.min_lat
        )

    def _cell_of(self, point: GeoPoint) -> tuple[int, int]:
        rows, cols = self._slope_deg.shape
        col = math.floor(
            (point.lon - self._extent.min_lon)
            / (self._extent.max_lon - self._extent.min_lon)
            * cols
        )
        row = math.floor(
            (self._extent.max_lat - point.lat)
            / (self._extent.max_lat - self._extent.min_lat)
            * rows
        )
        return row, col

    def _extract(
        self, row0: int, row1: int, col0: int, col1: int
    ) -> SlopeWindow:
        rows, cols = self._slope_deg.shape
        window = np.full((row1 - row0, col1 - col0), np.nan)
        src_r0 = max(row0, 0)
        src_r1 = min(row1, rows)
        src_c0 = max(col0, 0)
        src_c1 = min(col1, cols)
        if src_r0 < src_r1 and src_c0 < src_c1:
            window[
                src_r0 - row0 : src_r1 - row0,
                src_c0 - col0 : src_c1 - col0,
            ] = self._slope_deg[src_r0:src_r1, src_c0:src_c1]
        return SlopeWindow(
            slope_deg=window,
            cell_size_x_m=self._cell_size_x_m,
            cell_size_y_m=self._cell_size_y_m,
        )
