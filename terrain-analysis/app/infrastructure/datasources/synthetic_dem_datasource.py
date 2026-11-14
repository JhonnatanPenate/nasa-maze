import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.errors.exceptions import DomainValidationError
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.grid_backed_raster_datasource import (
    GridBackedRasterDatasource,
)
from app.infrastructure.datasources.grid_geometry import GridGeometry


class SyntheticDemDatasource(GridBackedRasterDatasource):
    """Deterministic in-memory DEM behind the RasterDatasource port.

    The grid is north-up: row 0 is max_lat, column 0 is min_lon, and the
    resolution is derived from extent / shape. Used as the service default
    and for tests; `default()` builds the MVP Mars patch documented in the
    datasources README.
    """

    def __init__(
        self,
        elevation: np.ndarray,
        extent: BoundingBox,
        mapper: DemWindowMapper,
        max_window_cells: int,
        nodata: float | None = None,
    ) -> None:
        elevation = np.asarray(elevation)
        if elevation.ndim != 2 or 0 in elevation.shape:
            raise DomainValidationError(
                f"Synthetic DEM elevation must be a non-empty 2-D array, "
                f"got shape {elevation.shape}"
            )
        super().__init__(mapper, max_window_cells)
        self._elevation = elevation
        self._grid = GridGeometry(extent, elevation.shape[0], elevation.shape[1])
        self._nodata = nodata

    @classmethod
    def default(
        cls, mapper: DemWindowMapper, max_window_cells: int
    ) -> "SyntheticDemDatasource":
        """Deterministic MVP DEM: lon 77..78, lat 18..19, 1200x1200 cells.

        Elevation is -2500 m plus layered sinusoidal hills and a planar tilt
        (a few hundred metres of relief, mixing flat/moderate/steep slopes).
        A nodata hole covers lon 77.90..77.95, lat 18.90..18.95 so 404 paths
        are testable; the smoke coordinates (18.4, 77.5) and (18.5, 77.6)
        hold real data.
        """
        extent = BoundingBox(
            min_lon=77.0, min_lat=18.0, max_lon=78.0, max_lat=19.0
        )
        rows, cols = 1200, 1200
        nodata = -32768.0
        res_lon = (extent.max_lon - extent.min_lon) / cols
        res_lat = (extent.max_lat - extent.min_lat) / rows
        lons = extent.min_lon + (np.arange(cols) + 0.5) * res_lon
        lats = extent.max_lat - (np.arange(rows) + 0.5) * res_lat
        lon, lat = np.meshgrid(lons, lats)
        elevation = (
            -2500.0
            + 300.0 * np.sin(lon * 6.0) * np.cos(lat * 5.0)
            + 120.0 * np.sin(lon * 150.0 + 0.7) * np.cos(lat * 140.0)
            + 40.0 * np.sin(lon * 30.0) * np.sin(lat * 33.0)
            + (lon - 77.5) * 300.0
            + (lat - 18.5) * 200.0
        )
        hole = (
            (lon >= 77.90) & (lon <= 77.95)
            & (lat >= 18.90) & (lat <= 18.95)
        )
        elevation[hole] = nodata
        return cls(
            elevation, extent, mapper, max_window_cells, nodata=nodata
        )

    def _geometry(self) -> GridGeometry:
        return self._grid

    def _read(
        self, row_slice: slice, col_slice: slice
    ) -> tuple[np.ndarray, float | None]:
        return self._elevation[row_slice, col_slice], self._nodata

    def ping(self) -> bool:
        return True
