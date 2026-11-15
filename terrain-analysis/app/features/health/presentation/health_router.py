from fastapi import APIRouter, Depends

from app.composition.dependencies import (
    get_settings,
    get_terrain_repository,
)
from app.core.config.settings import Settings
from app.core.ports.terrain_repository import TerrainRepository
from app.features.health.presentation.health_schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    repository: TerrainRepository = Depends(get_terrain_repository),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Liveness + datasource connectivity. Always answers 200; a failing
    or unbuildable datasource reports `degraded`/`unavailable` instead of
    an error (build failures surface as UnavailableRasterDatasource via
    get_raster_datasource, whose ping() is False). `datasource_kind`
    echoes the configured datasource so operators can tell DEM mode from
    grid mode."""
    if repository.is_available():
        return HealthResponse(
            status="ok",
            datasource="ok",
            datasource_kind=settings.datasource_kind,
        )
    return HealthResponse(
        status="degraded",
        datasource="unavailable",
        datasource_kind=settings.datasource_kind,
    )
