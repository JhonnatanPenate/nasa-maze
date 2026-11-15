from abc import ABC, abstractmethod

import numpy as np

from app.core.ports.raw_raster_metadata import RawRasterMetadata


class RasterDatasource(ABC):
    """Raw data access for a single raster dataset (one instance per file).

    Implementations do I/O only: coordinate-to-cell math lives in the
    domain GridGeometry, and slices passed to read_cells are already
    clipped inside the grid.
    """

    @abstractmethod
    def read_metadata(self) -> RawRasterMetadata:
        """File extent, shape, band descriptions, nodata sentinel and
        structural flags (geographic CRS, north-up)."""

    @abstractmethod
    def read_cells(
        self, band_index: int, rows: slice, cols: slice
    ) -> np.ndarray:
        """Raw cell values for a 1-based band index over in-grid slices."""

    @abstractmethod
    def ping(self) -> bool:
        """True when the underlying dataset is readable right now."""
