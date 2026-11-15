from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.composition.dependencies import get_repository
from app.core.domain.geo_point import GeoPoint
from app.core.ports.raster_repository import RasterRepository
from app.features.point_query.application.query_point import QueryPoint
from app.features.point_query.presentation.point_mapper import PointMapper
from app.features.point_query.presentation.point_schemas import (
    PointResponse,
)

router = APIRouter(prefix="/raster", tags=["raster"])


@router.get("/{dataset}/point", response_model=PointResponse)
def query_point(
    dataset: str,
    lat: Annotated[float, Query(description="Planetocentric latitude")],
    lon: Annotated[float, Query(description="Planetocentric longitude")],
    band: Annotated[
        str | None,
        Query(description="Band name; default returns all bands"),
    ] = None,
    repository: RasterRepository = Depends(get_repository),
) -> PointResponse:
    point = GeoPoint(lat=lat, lon=lon)
    result = QueryPoint(repository).execute(dataset, point, band or None)
    return PointMapper.to_response(result)
