from fastapi import APIRouter, Depends

from app.composition.dependencies import get_terrain_repository
from app.core.ports.terrain_repository import TerrainRepository
from app.features.health.presentation.health_schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    repository: TerrainRepository = Depends(get_terrain_repository),
) -> HealthResponse:
    """Liveness + datasource connectivity. Always answers 200; a failing
    or unbuildable datasource reports `degraded`/`unavailable` instead of
    an error (build failures surface as UnavailableRasterDatasource via
    get_raster_datasource, whose ping() is False)."""
    if repository.is_available():
        return HealthResponse(status="ok", datasource="ok")
    return HealthResponse(status="degraded", datasource="unavailable")
