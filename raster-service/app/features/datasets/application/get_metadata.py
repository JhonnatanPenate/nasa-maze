from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.ports.raster_repository import RasterRepository


class GetMetadata:
    """Domain metadata for one registered dataset.

    UnknownDatasetError -> 404 and DatasetUnavailableError -> 503 are
    raised by the repository.
    """

    def __init__(self, repository: RasterRepository) -> None:
        self._repository = repository

    def execute(self, dataset: str) -> DatasetMetadata:
        return self._repository.metadata(dataset)
