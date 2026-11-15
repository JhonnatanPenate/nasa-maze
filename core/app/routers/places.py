import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.clients.location_client import LocationUnavailableError, search_places
from app.routers.deps import get_transport
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api/lugares", tags=["lugares"])


@router.get("/buscar")
def buscar(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    settings: Settings = Depends(get_settings),
    transport: httpx.BaseTransport | None = Depends(get_transport),
):
    if not settings.ms1_url:
        raise HTTPException(503, "location-service no configurado")
    try:
        resp = search_places(settings.ms1_url, {"q": q, "limit": limit}, settings.search_timeout_s, transport)
    except LocationUnavailableError:
        raise HTTPException(503, "location-service no disponible")
    return JSONResponse(resp.json(), status_code=resp.status_code)
