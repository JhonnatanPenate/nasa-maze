"""MS6 Routing Engine: lowest-cost route to a mineral target in Gale Crater.

Extracted from planetary-explorer-fase2-3/backend/main.py (Javier Galdámez), only POST /api/ruta.
The optimizer lives in science/optimizador_rutas.py and is imported unchanged.
"""
from __future__ import annotations

import os
import sys
import threading
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / os.environ.get("MS6_DATA_DIR", "data/gale")
SCIENCE = ROOT / os.environ.get("MS6_SCIENCE_DIR", "science")
sys.path.insert(0, str(SCIENCE))

import optimizador_rutas as opt  # noqa: E402

SOLS = (1360, 2140, 3290, 4710)
AOI = (137.345, -4.740, 137.455, -4.580)  # west, south, east, north (IAU_2015:49900)
COLUMNAS_TRAMOS = [
    "tramo", "hora_lmst_inicio", "hora_lmst_fin", "tipo_suelo", "modelo_usado", "r2_ajustado",
    "distancia_m", "inclinacion_media_grados", "inclinacion_max_grados", "dosis_tramo_uGy",
    "dosis_acumulada_uGy", "temp_suelo_K",
]

_env_cache: dict[int, opt.MapaMision] = {}
# ponytail: global lock; pass vmax as a parameter if this needs to scale
_lock = threading.Lock()


def get_env(sol: int) -> opt.MapaMision:
    if sol not in _env_cache:
        _env_cache[sol] = opt.MapaMision(str(DATA), sol)
    return _env_cache[sol]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Pre-warm the demo's reference routes (Bradbury, sol 1360, 09:00 LMST) so the first click is instant
    for material in ("hematita", "esmectitas", "tridimita"):
        compute_route(137.4416, -4.5895, material, 1360, 9.0, 1000.0)
    yield


app = FastAPI(title="MS6 Routing Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RutaRequest(BaseModel):
    lon: float = Field(137.4416, description="Origin longitude (deg, IAU_2015:49900)")
    lat: float = Field(-4.5895, description="Origin latitude (deg, IAU_2015:49900)")
    material: Literal["hematita", "esmectitas", "tridimita", "sulfatos"] = Field(
        "hematita", description="Target mineral: hematite, smectites, tridymite or sulfates")
    sol: int = Field(1360, description="RAD/REMS reference sol: 1360, 2140, 3290 or 4710")
    hora: float = Field(9.0, ge=0, lt=24, description="Departure time, local mean solar time (LMST hours)")
    vmax: float = Field(1000.0, gt=0, description="Nominal walking speed (m/h)")


@app.get("/health")
def health():
    return {"status": "ok", "sols_disponibles": list(SOLS), "aoi": AOI}


@app.post("/route")
def route(req: RutaRequest):
    if req.sol not in SOLS:
        raise HTTPException(400, f"sol must be one of {list(SOLS)}")
    if not (AOI[0] <= req.lon <= AOI[2] and AOI[1] <= req.lat <= AOI[3]):
        raise HTTPException(400, f"origin is outside the Gale AOI {list(AOI)}")
    return compute_route(req.lon, req.lat, req.material, req.sol, req.hora, req.vmax)


# ponytail: per-process cache; every Cloud Run instance warms its own. Inputs and data are static,
# so the same request always yields the same route. Errors (HTTPException) are not cached.
@lru_cache(maxsize=64)
def compute_route(lon: float, lat: float, material: str, sol: int, hora: float, vmax: float) -> dict:
    with _lock:
        # The A* reads the canonical global VELOCIDAD_MAXIMA_M_H (not a loose alias).
        opt.VELOCIDAD_MAXIMA_M_H = opt.V_MAX_M_H = float(vmax)
        env = get_env(sol)
        if not env.control_calidad.get("cobertura_ok", True):
            raise HTTPException(422, "Map quality check failed: valid cell coverage < 90%")
        res = opt.calcular_ruta_optima(env, lon, lat, material, hora)
    if res is None:
        raise HTTPException(404, "No feasible route between origin and mineral target")

    ruta = res["ruta"]
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [list(env.centro(a["i"], a["j"])), list(env.centro(b["i"], b["j"]))],
            },
            "properties": {
                "capa": "ruta_optima",
                "tipo_suelo": str(env.tipo_suelo[b["i"], b["j"]]),
                "modelo_usado": str(env.nombre_modelo[b["i"], b["j"]]),
                "inclinacion_grados": float(env.inclinacion_predicha[b["i"], b["j"]]),
            },
        }
        for a, b in zip(ruta[:-1], ruta[1:])
    ]
    features += [
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [list(env.centro(n["i"], n["j"])) for n in res["ruta_modelo_global"]],
            },
            "properties": {"capa": "contrafactual", "nombre": "ruta_modelo_global"},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(res["objetivo"].lon), float(res["objetivo"].lat)]},
            "properties": {"capa": "objetivo", "nombre": res["objetivo"].nombre, "material": material},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"capa": "origen", "nombre": "origen"},
        },
    ]

    r, bag = res["resumen"], res["bagnold"]
    resumen = {
        "distancia_km": r["distancia_km"],
        "hora_llegada": r["llegada_lmst"],
        "dosis_rad_acum_uGy": float(r["dosis_uGy"]),
        "horas_espera_nocturna": float(r["espera_nocturna_h"]),
        "costo_objetivo": float(r["costo_objetivo"]),
        "nodos_expandidos": int(r["nodos_expandidos"]),
        "objetivo": r["objetivo_mineral"],
        "material": material,
        "comparativa_bagnold": {
            "celdas_duna_ruta_optima": int(bag["celdas_arena_ruta_optima"]),
            "celdas_duna_contrafactual": int(bag["ruta_modelo_global"]["celdas_arena"]),
            "horas_ahorradas_en_arena": float(bag["horas_ahorradas_en_arena"]),
            "distancia_minima_a_duna_m": int(bag["distancia_minima_a_duna_m"]),
        },
    }
    return {
        "geojson": {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "IAU_2015:49900"}},
            "features": features,
        },
        "resumen": resumen,
        "tramos": res["tramos"][COLUMNAS_TRAMOS].to_dict(orient="records"),
        "control_calidad": env.control_calidad,
    }
