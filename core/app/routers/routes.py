from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.clients.risk_client import evaluate_route
from app.clients.routing_client import RoutingClient, RoutingUnavailableError
from app.datasources import precalculated_routes as precalc
from app.routers.deps import get_transport
from app.settings import Settings, get_settings

router = APIRouter(prefix="/api", tags=["ruta"])


class RutaRequest(BaseModel):
    lon: float = 137.4416
    lat: float = -4.5895
    material: Literal["hematita", "esmectitas", "tridimita", "sulfatos"] = "hematita"
    sol: int = 1360
    hora: float = Field(9.0, ge=0, lt=24)
    vmax: float = Field(1000.0, gt=0)


def _con_riesgo(body: dict, req: RutaRequest, settings: Settings, transport: httpx.BaseTransport | None) -> dict:
    riesgo = None
    if settings.ms5_url:
        riesgo = evaluate_route(settings.ms5_url, body["geojson"], req.sol, req.hora, settings.risk_timeout_s, transport)
    return {**body, "riesgo": riesgo}


@router.post("/ruta")
def ruta(
    req: RutaRequest,
    settings: Settings = Depends(get_settings),
    transport: httpx.BaseTransport | None = Depends(get_transport),
):
    if settings.ms6_url:
        try:
            resp = RoutingClient(settings.ms6_url, settings.route_timeout_s, transport).post_route(req.model_dump())
        except RoutingUnavailableError:
            pass
        else:
            body = resp.json()
            if resp.is_success:
                body = _con_riesgo({**body, "fuente": "ms6"}, req, settings, transport)
            return JSONResponse(body, status_code=resp.status_code)

    if settings.precalc_fallback and precalc.es_elegible(req, settings.bradbury_lon, settings.bradbury_lat):
        body = {**precalc.cargar_ruta(settings.processed, req.material), "fuente": "precalculada"}
        return _con_riesgo(body, req, settings, transport)

    raise HTTPException(503, "sin backend de ruta disponible para esta solicitud")
