from fastapi import APIRouter, Depends

from app.composition.dependencies import get_repository
from app.core.ports.raster_repository import RasterRepository
from app.features.health.presentation.health_schemas import (
    DatasetHealth,
    HealthResponse,
)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    repository: RasterRepository = Depends(get_repository),
) -> HealthResponse:
    """Liveness + per-dataset readability. Always answers 200; any
    unreadable dataset flips `status` to `degraded`."""
    datasets = [
        DatasetHealth(name=name, readable=repository.is_readable(name))
        for name in repository.dataset_names()
    ]
    status = "ok" if all(d.readable for d in datasets) else "degraded"
    return HealthResponse(
        status=status, dataset_count=len(datasets), datasets=datasets
    )
