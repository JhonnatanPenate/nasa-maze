import numpy as np

from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raw_raster_metadata import RawRasterMetadata


class FailingRasterDatasource(RasterDatasource):
    """RasterDatasource stub whose calls always fail with OSError.

    Reusable by repository and API tests that need the 503 failure path.
    """

    def read_metadata(self) -> RawRasterMetadata:
        raise OSError("failing datasource: read_metadata unavailable")

    def read_cells(
        self, band_index: int, rows: slice, cols: slice
    ) -> np.ndarray:
        raise OSError("failing datasource: read_cells unavailable")

    def ping(self) -> bool:
        return False
