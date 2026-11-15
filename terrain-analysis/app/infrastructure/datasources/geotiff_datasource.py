import numpy as np
import rasterio
from rasterio.windows import Window

from app.core.domain.bounding_box import BoundingBox
from app.core.errors.exceptions import UpstreamDatasourceError
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.grid_backed_raster_datasource import (
    GridBackedRasterDatasource,
)
from app.infrastructure.datasources.grid_geometry import GridGeometry


class GeoTiffRasterDatasource(GridBackedRasterDatasource):
    """RasterDatasource reading windows from a GeoTIFF via rasterio.

    Requires a geographic lon/lat (degrees), north-up, non-rotated CRS —
    validated on each open. `band` selects the raster band read (1-based);
    for the rejilla slope grid it is `Settings.rejilla_slope_band`. The
    dataset is opened lazily per call and reads use rasterio windows, so
    point queries never load the whole raster. Opening/reading errors
    propagate; the repository wraps them as UpstreamDatasourceError.
    """

    def __init__(
        self,
        path: str,
        mapper: DemWindowMapper,
        max_window_cells: int,
        band: int = 1,
    ) -> None:
        super().__init__(mapper, max_window_cells)
        self._path = str(path)
        self._band = band

    def _geometry(self) -> GridGeometry:
        with rasterio.open(self._path) as ds:
            self._validate(ds)
            bounds = ds.bounds
            extent = BoundingBox(
                min_lon=bounds.left,
                min_lat=bounds.bottom,
                max_lon=bounds.right,
                max_lat=bounds.top,
            )
            return GridGeometry(extent, ds.height, ds.width)

    def _read(
        self, row_slice: slice, col_slice: slice
    ) -> tuple[np.ndarray, float | None]:
        with rasterio.open(self._path) as ds:
            raw = ds.read(
                self._band,
                window=Window(
                    col_slice.start,
                    row_slice.start,
                    col_slice.stop - col_slice.start,
                    row_slice.stop - row_slice.start,
                ),
            )
            return raw, ds.nodata

    def ping(self) -> bool:
        try:
            with rasterio.open(self._path) as ds:
                self._validate(ds)
            return True
        except Exception:
            return False

    def _validate(self, ds) -> None:
        if not 1 <= self._band <= ds.count:
            raise UpstreamDatasourceError(
                f"{self._path}: band {self._band} out of range "
                f"(raster has {ds.count} band(s))"
            )
        if ds.crs is not None and not ds.crs.is_geographic:
            raise UpstreamDatasourceError(
                f"{self._path}: CRS {ds.crs} is not geographic "
                f"(lon/lat degrees required)"
            )
        transform = ds.transform
        if transform.b != 0.0 or transform.d != 0.0:
            raise UpstreamDatasourceError(
                f"{self._path}: rotated/sheared rasters are not supported"
            )
        if transform.e >= 0.0:
            raise UpstreamDatasourceError(
                f"{self._path}: raster is not north-up"
            )
