from app.core.ports.raster_repository import RasterRepository


class ListDatasets:
    """List registered datasets as (name, readable) pairs.

    Never reads metadata, so an unreadable dataset is reported with
    `readable=False` instead of failing the listing. The configured path
    is not part of the RasterRepository port; the router merges it from
    Settings.
    """

    def __init__(self, repository: RasterRepository) -> None:
        self._repository = repository

    def execute(self) -> list[tuple[str, bool]]:
        return [
            (name, self._repository.is_readable(name))
            for name in self._repository.dataset_names()
        ]
