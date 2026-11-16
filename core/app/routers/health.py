import httpx
from fastapi import APIRouter, Depends

from app.clients.service_registry import ping
from app.datasources.precalculated_routes import disponible
from app.datasources.raster_layers import rejilla_bounds
from app.routers.deps import get_transport
from app.settings import AOI, SOLS, DataUnavailableError, Settings, get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings), transport: httpx.BaseTransport | None = Depends(get_transport)):
    servicios = {
        name: ping(url, settings.health_timeout_s, transport)
        for name, url in (
            ("ms6", settings.ms6_url),
            ("ms5", settings.ms5_url),
            ("ms4", settings.ms4_url),
            ("ms1", settings.ms1_url),
        )
    }
    fallback = settings.precalc_fallback and disponible(settings.processed)
    try:
        bounds = rejilla_bounds(settings.processed)
    except DataUnavailableError:
        bounds = None
    return {
        "status": "ok" if servicios["ms6"] == "ok" or fallback else "degraded",
        "servicios": servicios,
        "fallback_precalculado": fallback,
        "aoi": AOI,
        "sols": SOLS,
        "bounds_rejilla": bounds,
    }
