import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.settings import AOI, DataUnavailableError

CRS = {"type": "name", "properties": {"name": "IAU_2015:49900"}}


def _en_aoi(coords) -> bool:
    return any(AOI[0] <= c[0] <= AOI[2] and AOI[1] <= c[1] <= AOI[3] for c in coords)


def _puntos(xlsx: Path) -> list[dict]:
    df = pd.read_excel(xlsx).astype(object)
    df = df.where(df.notna(), None)
    return [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {"capa": "puntos_quimica", **{k: v for k, v in r.items() if k not in ("lon", "lat")}},
        }
        for r in df.to_dict(orient="records")
    ]


def _traza(vectores: Path) -> list[dict]:
    traverse = json.loads(vectores.read_text(encoding="utf-8"))["MSL_traverse"]["features"]
    lineas = [
        line
        for f in traverse
        for line in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiLineString" else [f["geometry"]["coordinates"]])
        if _en_aoi(line)
    ]
    lineas = [[c[:2] for c in line] for line in lineas]
    return [
        {
            "type": "Feature",
            "geometry": {"type": "MultiLineString", "coordinates": lineas},
            "properties": {"capa": "traza_msl"},
        }
    ]


@lru_cache
def load_base_layers(processed: Path, raw: Path, lon: float, lat: float) -> dict:
    try:
        features = _puntos(processed / "gale_puntos_quimica.xlsx") + _traza(raw / "pe_msl_vectores.json")
    except (OSError, ValueError, KeyError) as e:
        raise DataUnavailableError(f"capas base ilegibles: {e}") from e
    features.append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"capa": "origen", "nombre": "Bradbury Landing"},
        }
    )
    return {"type": "FeatureCollection", "crs": CRS, "features": features}
