from typing import Literal

from fastapi import APIRouter, Depends, Path, Response

from app.datasources.base_layers import load_base_layers
from app.datasources.raster_layers import BANDAS, render_band
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/capas", tags=["capas"])

Banda = Literal[BANDAS]


@router.get("/base")
def capas_base(settings: Settings = Depends(get_settings)):
    return load_base_layers(settings.processed, settings.raw, settings.bradbury_lon, settings.bradbury_lat)


@router.get("/raster/{banda}")
def capa_raster(
    banda: Banda = Path(...),
    cmap: Literal["viridis", "gray"] = "viridis",
    settings: Settings = Depends(get_settings),
):
    png, bounds = render_band(settings.processed, banda, cmap)
    return Response(png, media_type="image/png", headers={"X-Bounds": ",".join(f"{v:.6f}" for v in bounds)})
