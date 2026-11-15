import numpy as np

from app.core.domain.bounding_box import BoundingBox
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raw_raster_metadata import RawRasterMetadata


class InMemoryRasterDatasource(RasterDatasource):
    """RasterDatasource serving a 3-D numpy array (bands x rows x cols).

    Used for dev/tests and the `DatasetConfig.kind == "memory"` swap
    point. `synthetic()` builds a deterministic stand-in for the rejilla
    grid so the service can run demos without the delivered GeoTIFF.
    """

    def __init__(
        self,
        cells: np.ndarray,
        extent: BoundingBox,
        band_descriptions: tuple[str | None, ...] | None = None,
        nodata: float | None = None,
    ) -> None:
        cells = np.asarray(cells)
        if cells.ndim != 3:
            raise ValueError(
                f"cells must be a 3-D (bands, rows, cols) array, "
                f"got shape {cells.shape}"
            )
        band_count = cells.shape[0]
        if band_descriptions is None:
            band_descriptions = (None,) * band_count
        if len(band_descriptions) != band_count:
            raise ValueError(
                f"band_descriptions has {len(band_descriptions)} entries "
                f"for {band_count} bands"
            )
        self._cells = cells
        self._extent = extent
        self._band_descriptions = tuple(band_descriptions)
        self._nodata = nodata

    @classmethod
    def synthetic(cls) -> "InMemoryRasterDatasource":
        """Deterministic synthetic rejilla: 6 canonical bands over the
        nominal Gale AOI (105 x 72), with one NaN nodata cell."""
        rows, cols = 105, 72
        extent = BoundingBox(
            min_lon=137.345, min_lat=-4.740, max_lon=137.455, max_lat=-4.580
        )
        row_idx, col_idx = np.meshgrid(
            np.arange(rows, dtype=np.float64),
            np.arange(cols, dtype=np.float64),
            indexing="ij",
        )
        cells = np.stack(
            [
                35.0 * (row_idx + col_idx) / (rows + cols - 2),
                0.1 + 5.0 * row_idx / (rows - 1),
                col_idx / (cols - 1),
                400.0 + 45.0 * np.sin(row_idx * 0.35) * np.cos(col_idx * 0.2),
                np.full((rows, cols), 0.23),
                5400.0 * (row_idx * col_idx) / ((rows - 1) * (cols - 1)),
            ]
        ).astype(np.float32)
        cells[2, 0, 0] = np.nan
        return cls(
            cells,
            extent,
            band_descriptions=(
                "pendiente_grados",
                "rugosidad_m",
                "fraccion_oscura",
                "inercia_termica_tiu",
                "albedo",
                "distancia_duna_m",
            ),
            nodata=None,
        )

    def read_metadata(self) -> RawRasterMetadata:
        return RawRasterMetadata(
            extent=self._extent,
            rows=self._cells.shape[1],
            cols=self._cells.shape[2],
            band_descriptions=self._band_descriptions,
            nodata=self._nodata,
            is_geographic=True,
            is_north_up=True,
        )

    def read_cells(
        self, band_index: int, rows: slice, cols: slice
    ) -> np.ndarray:
        if not 1 <= band_index <= self._cells.shape[0]:
            raise IndexError(
                f"band index {band_index} out of range "
                f"(datasource has {self._cells.shape[0]} band(s))"
            )
        rows = _normalise(rows, self._cells.shape[1])
        cols = _normalise(cols, self._cells.shape[2])
        return self._cells[band_index - 1, rows, cols].copy()

    def ping(self) -> bool:
        return True


def _normalise(selection: slice, size: int) -> slice:
    if selection.step not in (None, 1):
        raise ValueError(
            f"slice step must be 1, got {selection.step!r}"
        )
    return slice(*selection.indices(size))
