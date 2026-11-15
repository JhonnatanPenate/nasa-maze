"""MS6 Routing Engine: ruta de costo mínimo hacia un mineral objetivo en Gale.

Extraído de planetary-explorer-fase2-3/backend/main.py (Javier Galdámez), solo POST /api/ruta.
El optimizador vive en science/optimizador_rutas.py y se importa tal cual.
"""
from __future__ import annotations

import os
import sys
import threading
from contextlib import asynccontextmanager
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
# ponytail: lock global; pasar vmax como parámetro si escala
_lock = threading.Lock()


def get_env(sol: int) -> opt.MapaMision:
    if sol not in _env_cache:
        _env_cache[sol] = opt.MapaMision(str(DATA), sol)
    return _env_cache[sol]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_env(1360)  # precarga el sol por defecto; el resto bajo demanda
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
    lon: float = Field(137.4416, description="Longitud origen")
    lat: float = Field(-4.5895, description="Latitud origen")
    material: Literal["hematita", "esmectitas", "tridimita", "sulfatos"] = "hematita"
    sol: int = Field(1360, description="Sol de referencia RAD/REMS")
    hora: float = Field(9.0, ge=0, lt=24, description="Hora LMST de salida")
    vmax: float = Field(1000.0, gt=0, description="Velocidad nominal m/h")


@app.get("/health")
def health():
    return {"status": "ok", "sols_disponibles": list(SOLS), "aoi": AOI}


@app.post("/route")
def route(req: RutaRequest):
    if req.sol not in SOLS:
        raise HTTPException(400, f"sol debe ser uno de {list(SOLS)}")
    if not (AOI[0] <= req.lon <= AOI[2] and AOI[1] <= req.lat <= AOI[3]):
        raise HTTPException(400, f"origen fuera del AOI de Gale {list(AOI)}")

    with _lock:
        # La A* lee el global canónico VELOCIDAD_MAXIMA_M_H (no un alias suelto).
        opt.VELOCIDAD_MAXIMA_M_H = opt.V_MAX_M_H = float(req.vmax)
        env = get_env(req.sol)
        if not env.control_calidad.get("cobertura_ok", True):
            raise HTTPException(422, "Control de calidad fallido: cobertura de celdas < 90%")
        res = opt.calcular_ruta_optima(env, req.lon, req.lat, req.material, req.hora)
    if res is None:
        raise HTTPException(404, "Sin ruta factible entre origen y objetivo mineral")

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
            "properties": {"capa": "objetivo", "nombre": res["objetivo"].nombre, "material": req.material},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [req.lon, req.lat]},
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
        "material": req.material,
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
