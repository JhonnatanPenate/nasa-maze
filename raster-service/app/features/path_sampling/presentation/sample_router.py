from fastapi import APIRouter, Depends

from app.composition.dependencies import get_repository, get_settings
from app.core.config.settings import Settings
from app.core.domain.geo_point import GeoPoint
from app.core.ports.raster_repository import RasterRepository
from app.features.path_sampling.application.sample_path import SamplePath
from app.features.path_sampling.presentation.sample_mapper import (
    SampleMapper,
)
from app.features.path_sampling.presentation.sample_schemas import (
    SampleRequest,
    SampleResponse,
)

router = APIRouter(prefix="/raster", tags=["raster"])


@router.post("/{dataset}/sample", response_model=SampleResponse)
def sample_path(
    dataset: str,
    request: SampleRequest,
    repository: RasterRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
) -> SampleResponse:
    path = [GeoPoint(lat=point.lat, lon=point.lon) for point in request.path]
    result = SamplePath(
        repository,
        planet_radius_km=settings.planet_radius_km,
        max_path_points=settings.max_path_points,
        max_samples=settings.max_samples,
    ).execute(dataset, path, request.band, request.sample_distance_m)
    return SampleMapper.to_response(result)
