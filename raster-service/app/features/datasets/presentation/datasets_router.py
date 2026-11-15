from fastapi import APIRouter, Depends

from app.composition.dependencies import get_repository, get_settings
from app.core.config.settings import Settings
from app.core.ports.raster_repository import RasterRepository
from app.features.datasets.application.get_metadata import GetMetadata
from app.features.datasets.application.list_datasets import ListDatasets
from app.features.datasets.presentation.datasets_mapper import (
    DatasetsMapper,
)
from app.features.datasets.presentation.datasets_schemas import (
    DatasetsResponse,
    MetadataResponse,
)

router = APIRouter(prefix="/raster", tags=["raster"])


@router.get("/datasets", response_model=DatasetsResponse)
def list_datasets(
    repository: RasterRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> DatasetsResponse:
    entries = ListDatasets(repository).execute()
    paths = {
        name: config.path for name, config in (settings.datasets or {}).items()
    }
    return DatasetsMapper.to_datasets_response(entries, paths)


@router.get("/{dataset}/metadata", response_model=MetadataResponse)
def get_metadata(
    dataset: str,
    repository: RasterRepository = Depends(get_repository),
) -> MetadataResponse:
    metadata = GetMetadata(repository).execute(dataset)
    return DatasetsMapper.to_metadata_response(metadata)
