from typing import Literal

from fastapi import APIRouter, Depends

from app.composition.dependencies import (
    get_environment_repository,
    get_raster_source,
    get_settings,
    get_terrain_source,
)
from app.core.config.settings import Settings
from app.core.ports.environment_repository import EnvironmentRepository
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.features.health.presentation.health_schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    terrain: TerrainSource = Depends(get_terrain_source),
    raster: RasterSource = Depends(get_raster_source),
    environment: EnvironmentRepository = Depends(get_environment_repository),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Liveness + upstream connectivity (SPEC §6). Always answers 200;
    unreachable upstreams report `unavailable` and the service `degraded`."""
    terrain_ok = terrain.ping()
    raster_ok = raster.ping()
    env_ok = environment.ping()
    status: Literal["ok", "degraded"] = (
        "ok" if (terrain_ok and raster_ok and env_ok) else "degraded"
    )
    return HealthResponse(
        status=status,
        datasource_mode=settings.datasource_mode,
        terrain="ok" if terrain_ok else "unavailable",
        raster="ok" if raster_ok else "unavailable",
        environment="ok" if env_ok else "unavailable",
    )
