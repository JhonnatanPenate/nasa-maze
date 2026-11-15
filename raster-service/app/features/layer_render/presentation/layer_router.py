from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.composition.dependencies import (
    get_image_encoder,
    get_repository,
)
from app.core.ports.image_encoder import ImageEncoder
from app.core.ports.raster_repository import RasterRepository
from app.features.layer_render.application.render_layer import RenderLayer

router = APIRouter(prefix="/raster", tags=["raster"])


@router.get("/{dataset}/layer/{band}")
def render_layer(
    dataset: str,
    band: str,
    colormap: Annotated[
        str | None,
        Query(description="Colormap name; default per band from config"),
    ] = None,
    repository: RasterRepository = Depends(get_repository),
    encoder: ImageEncoder = Depends(get_image_encoder),
) -> Response:
    layer = RenderLayer(repository, encoder).execute(
        dataset, band, colormap
    )
    bounds = layer.bounds
    low, high = layer.value_range
    return Response(
        content=layer.png,
        media_type="image/png",
        headers={
            "X-Raster-Bounds": (
                f"{bounds.min_lon},{bounds.min_lat},"
                f"{bounds.max_lon},{bounds.max_lat}"
            ),
            "X-Raster-CRS": layer.crs,
            "X-Raster-Value-Range": f"{low},{high}",
        },
    )
