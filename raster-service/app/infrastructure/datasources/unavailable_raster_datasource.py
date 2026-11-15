import numpy as np

from app.core.errors.exceptions import DatasetUnavailableError
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raw_raster_metadata import RawRasterMetadata


class UnavailableRasterDatasource(RasterDatasource):
    """Stand-in for a datasource that failed to build at wiring time.

    Created by the composition root when `build_datasource` raises.
    `ping()` reports False so `/health` degrades, and every read
    re-raises the stored failure as DatasetUnavailableError (HTTP 503).
    """

    def __init__(self, error: Exception) -> None:
        self._error = error

    def read_metadata(self) -> RawRasterMetadata:
        raise DatasetUnavailableError(
            f"Raster datasource unavailable: {self._error}"
        ) from self._error

    def read_cells(
        self, band_index: int, rows: slice, cols: slice
    ) -> np.ndarray:
        raise DatasetUnavailableError(
            f"Raster datasource unavailable: {self._error}"
        ) from self._error

    def ping(self) -> bool:
        return False
