from fastapi import APIRouter, Depends

from app.composition.dependencies import get_repository, get_settings
from app.core.config.settings import Settings
from app.core.ports.raster_repository import RasterRepository
from app.features.window_read.application.read_window import ReadWindow
from app.features.window_read.presentation.window_mapper import (
    WindowMapper,
)
from app.features.window_read.presentation.window_schemas import (
    WindowRequestSchema,
    WindowResponse,
)

router = APIRouter(prefix="/raster", tags=["raster"])


@router.post("/{dataset}/window", response_model=WindowResponse)
def read_window(
    dataset: str,
    body: WindowRequestSchema,
    repository: RasterRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> WindowResponse:
    request = WindowMapper.to_domain(body)
    metadata, window, cells, center_lat = ReadWindow(
        repository, settings.max_window_cells
    ).execute(dataset, request)
    return WindowMapper.to_response(
        metadata.band(request.band).name, metadata, window, cells,
        center_lat,
    )
