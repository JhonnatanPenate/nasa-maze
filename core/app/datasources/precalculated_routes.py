import json
from pathlib import Path

import pandas as pd

from app.settings import DataUnavailableError

MATERIALES = ("hematita", "esmectitas", "tridimita")
SOL, HORA, VMAX = 1360, 9.0, 1000.0
TOLERANCIA_GRADOS = 0.0015  # ~1 celda de 90 m
COLUMNAS_TRAMOS = [
    "tramo", "hora_lmst_inicio", "hora_lmst_fin", "tipo_suelo", "modelo_usado", "r2_ajustado",
    "distancia_m", "inclinacion_media_grados", "inclinacion_max_grados", "dosis_tramo_uGy",
    "dosis_acumulada_uGy", "temp_suelo_K",
]


def es_elegible(req, bradbury_lon: float, bradbury_lat: float) -> bool:
    return (
        req.material in MATERIALES
        and req.sol == SOL
        and req.hora == HORA
        and req.vmax == VMAX
        and abs(req.lon - bradbury_lon) <= TOLERANCIA_GRADOS
        and abs(req.lat - bradbury_lat) <= TOLERANCIA_GRADOS
    )


def disponible(processed: Path) -> bool:
    return all(
        (processed / f"ruta_{m}{s}").exists()
        for m in MATERIALES
        for s in (".geojson", "_tramos.xlsx", "_resumen.json")
    )


def cargar_ruta(processed: Path, material: str) -> dict:
    try:
        geo = json.loads((processed / f"ruta_{material}.geojson").read_text(encoding="utf-8"))
        res = json.loads((processed / f"ruta_{material}_resumen.json").read_text(encoding="utf-8"))
        tramos = pd.read_excel(processed / f"ruta_{material}_tramos.xlsx")
    except (OSError, ValueError) as e:
        raise DataUnavailableError(f"ruta precalculada de {material} ilegible: {e}") from e

    r, dunas = res["resumen"], res["comparativa_dunas"]
    segmentos = [f for f in geo["features"] if f["properties"].get("capa") == "ruta_optima"]
    contrafactual = [f for f in geo["features"] if f["properties"].get("capa") == "contrafactual"]
    camino = [c for f in segmentos for c in f["geometry"]["coordinates"]]
    puntos = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": camino[-1]},
            "properties": {"capa": "objetivo", "nombre": r["objetivo_mineral"], "material": material},
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": camino[0]},
            "properties": {"capa": "origen", "nombre": "origen"},
        },
    ]
    tabla = tramos[COLUMNAS_TRAMOS].astype(object)
    return {
        "geojson": {"type": "FeatureCollection", "crs": geo["crs"], "features": segmentos + contrafactual + puntos},
        "resumen": {
            "distancia_km": r["distancia_km"],
            "hora_llegada": r["llegada_lmst"],
            "dosis_rad_acum_uGy": float(r["dosis_uGy"]),
            "horas_espera_nocturna": float(r["espera_nocturna_h"]),
            "costo_objetivo": float(r["costo_objetivo"]),
            "nodos_expandidos": int(r["nodos_expandidos"]),
            "objetivo": r["objetivo_mineral"],
            "material": material,
            "comparativa_bagnold": {
                "celdas_duna_ruta_optima": int(dunas["celdas_arena_ruta_optima"]),
                "celdas_duna_contrafactual": int(dunas["ruta_modelo_global"]["celdas_arena"]),
                "horas_ahorradas_en_arena": float(dunas["horas_ahorradas_en_arena"]),
                "distancia_minima_a_duna_m": int(dunas["distancia_minima_a_duna_m"]),
            },
        },
        "tramos": tabla.where(tabla.notna(), None).to_dict(orient="records"),
        "control_calidad": res.get("control_calidad"),
    }
