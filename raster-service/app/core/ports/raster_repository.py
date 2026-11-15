from abc import ABC, abstractmethod

import numpy as np

from app.core.domain.dataset_metadata import DatasetMetadata


class RasterRepository(ABC):
    """Domain-facing access to the registered datasets.

    Use cases depend only on this port; implementations receive
    RasterDatasource instances by constructor and normalise raw values
    (nodata sentinel -> NaN, float64).
    """

    @abstractmethod
    def dataset_names(self) -> list[str]:
        """Names of all registered datasets."""

    @abstractmethod
    def metadata(self, dataset: str) -> DatasetMetadata:
        """UnknownDatasetError / DatasetUnavailableError on failure."""

    @abstractmethod
    def read_cells(
        self, dataset: str, band: str, rows: slice, cols: slice
    ) -> np.ndarray:
        """float64 cell values with the nodata sentinel converted to NaN."""

    @abstractmethod
    def is_readable(self, dataset: str) -> bool:
        """True when the dataset can be read right now (health check)."""
