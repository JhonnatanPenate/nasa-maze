import logging

import httpx

log = logging.getLogger(__name__)


def route_polyline(geojson: dict) -> list[dict]:
    """Vértices {lat, lon} de la ruta óptima a partir de sus segmentos [lon, lat]."""
    segs = [f["geometry"]["coordinates"] for f in geojson["features"] if f["properties"].get("capa") == "ruta_optima"]
    coords = [segs[0][0]] + [s[-1] for s in segs] if segs else []
    return [{"lat": c[1], "lon": c[0]} for c in coords]


def evaluate_route(
    base_url: str, geojson: dict, sol: int, hora: float, timeout_s: float, transport: httpx.BaseTransport | None = None
) -> dict | None:
    """Riesgo de MS5 a lo largo de la ruta; None si no se puede evaluar (nunca rompe la ruta)."""
    path = route_polyline(geojson)
    if len(path) < 2:
        return None
    payload = {"path": path, "sol": sol, "hora": int(hora)}
    try:
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport) as c:
            resp = c.post("/risk/evaluate", json=payload)
    except httpx.HTTPError as e:
        log.warning("MS5 no disponible: %s", e)
        return None
    if not resp.is_success:
        log.warning("MS5 respondió %s: %s", resp.status_code, resp.text[:200])
        return None
    return resp.json()
