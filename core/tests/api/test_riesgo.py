import json

import httpx

from app.clients.risk_client import route_polyline

MS6, MS5 = "http://ms6.test", "http://ms5.test"
REQ = {"lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9.0, "vmax": 1000}
RIESGO = {"overall_risk": 0.42, "risk_level": "medium", "segments": [], "blocking_segments": []}
MS6_BODY = {
    "geojson": {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[137.1, -4.1], [137.2, -4.2]]}, "properties": {"capa": "ruta_optima"}},
            {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[137.2, -4.2], [137.3, -4.3]]}, "properties": {"capa": "ruta_optima"}},
        ],
    },
    "resumen": {},
    "tramos": [],
    "control_calidad": {},
}


def servicios(seen, ms5=None, ms6=None):
    def handler(request: httpx.Request):
        seen.append((request.url.host, request.url.path, request.read()))
        if request.url.host == "ms5.test":
            return ms5(request) if ms5 else httpx.Response(200, json=RIESGO)
        return ms6(request) if ms6 else httpx.Response(200, json=MS6_BODY)

    return handler


def test_route_polyline_une_segmentos():
    assert route_polyline(MS6_BODY["geojson"]) == [
        {"lat": -4.1, "lon": 137.1}, {"lat": -4.2, "lon": 137.2}, {"lat": -4.3, "lon": 137.3},
    ]
    assert route_polyline({"features": []}) == []


def test_ruta_ms6_incluye_riesgo_de_ms5(make_client):
    seen = []
    r = make_client(servicios(seen), ms6_url=MS6, ms5_url=MS5).post("/api/ruta", json=REQ)
    body = r.json()
    assert r.status_code == 200 and body["fuente"] == "ms6" and body["riesgo"] == RIESGO
    host, path, raw = seen[-1]
    assert (host, path) == ("ms5.test", "/risk/evaluate")
    assert json.loads(raw) == {
        "path": [{"lat": -4.1, "lon": 137.1}, {"lat": -4.2, "lon": 137.2}, {"lat": -4.3, "lon": 137.3}],
        "sol": 1360,
        "hora": 9,
    }


def test_ruta_precalculada_incluye_riesgo(make_client):
    seen = []
    r = make_client(servicios(seen), ms5_url=MS5).post("/api/ruta", json=REQ)
    body = r.json()
    assert body["fuente"] == "precalculada" and body["riesgo"] == RIESGO
    assert len(json.loads(seen[-1][2])["path"]) == 67


def test_sin_ms5_configurado_riesgo_es_null(make_client):
    seen = []
    body = make_client(servicios(seen), ms6_url=MS6).post("/api/ruta", json=REQ).json()
    assert body["riesgo"] is None and all(h != "ms5.test" for h, _, _ in seen)


def test_ms5_caido_no_rompe_la_ruta(make_client):
    def caido(request):
        raise httpx.ConnectError("down")

    r = make_client(servicios([], ms5=caido), ms6_url=MS6, ms5_url=MS5).post("/api/ruta", json=REQ)
    assert r.status_code == 200 and r.json()["riesgo"] is None and r.json()["fuente"] == "ms6"


def test_ms5_error_http_no_rompe_la_ruta(make_client):
    for status in (400, 404, 502):
        h = servicios([], ms5=lambda request, s=status: httpx.Response(s, json={"detail": "x"}))
        body = make_client(h, ms6_url=MS6, ms5_url=MS5).post("/api/ruta", json=REQ).json()
        assert body["riesgo"] is None and "geojson" in body


def test_error_4xx_de_ms6_no_llama_a_ms5(make_client):
    seen = []
    h = servicios(seen, ms6=lambda request: httpx.Response(404, json={"detail": "Sin ruta"}))
    r = make_client(h, ms6_url=MS6, ms5_url=MS5).post("/api/ruta", json=REQ)
    assert r.status_code == 404 and all(host != "ms5.test" for host, _, _ in seen)


def test_health_incluye_ms5(make_client):
    h = lambda request: httpx.Response(200, json={"status": "ok"})
    assert make_client(h, ms5_url=MS5).get("/api/health").json()["servicios"]["ms5"] == "ok"
