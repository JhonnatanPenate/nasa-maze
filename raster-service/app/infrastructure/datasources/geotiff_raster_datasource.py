import numpy as np
import rasterio
from rasterio.windows import Window

from app.core.domain.bounding_box import BoundingBox
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raw_raster_metadata import RawRasterMetadata


class GeoTiffRasterDatasource(RasterDatasource):
    """RasterDatasource reading cell windows from a GeoTIFF via rasterio.

    The file is opened lazily per call — no handles are held across
    requests (spec §6). Read errors propagate; the repository wraps them
    as DatasetUnavailableError. Values are served verbatim in the file
    dtype; nodata normalisation happens in the repository.
    """

    def __init__(self, path) -> None:
        self._path = str(path)

    def read_metadata(self) -> RawRasterMetadata:
        with rasterio.open(self._path) as ds:
            bounds = ds.bounds
            transform = ds.transform
            unrotated = transform.b == 0.0 and transform.d == 0.0
            return RawRasterMetadata(
                extent=BoundingBox(
                    min_lon=bounds.left,
                    min_lat=bounds.bottom,
                    max_lon=bounds.right,
                    max_lat=bounds.top,
                ),
                rows=ds.height,
                cols=ds.width,
                band_descriptions=tuple(ds.descriptions),
                nodata=ds.nodata,
                is_geographic=bool(ds.crs) and ds.crs.is_geographic,
                is_north_up=unrotated and transform.e < 0.0,
            )

    def read_cells(
        self, band_index: int, rows: slice, cols: slice
    ) -> np.ndarray:
        with rasterio.open(self._path) as ds:
            rows = _normalise(rows, ds.height)
            cols = _normalise(cols, ds.width)
            return ds.read(
                band_index,
                window=Window(
                    cols.start,
                    rows.start,
                    cols.stop - cols.start,
                    rows.stop - rows.start,
                ),
            )

    def ping(self) -> bool:
        try:
            meta = self.read_metadata()
        except Exception:
            return False
        return meta.is_geographic and meta.is_north_up


def _normalise(selection: slice, size: int) -> slice:
    if selection.step not in (None, 1):
        raise ValueError(
            f"slice step must be 1, got {selection.step!r}"
        )
    return slice(*selection.indices(size))
