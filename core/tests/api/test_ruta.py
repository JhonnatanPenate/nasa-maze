import httpx

MS6 = "http://ms6.test"
REQ = {"lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9.0, "vmax": 1000}
CONTRATO = {"geojson", "resumen", "tramos", "control_calidad", "fuente", "riesgo"}


def test_ms6_passthrough(make_client):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"], seen["body"] = str(request.url), request.read()
        return httpx.Response(200, json={"geojson": {}, "resumen": {"distancia_km": 1}, "tramos": [], "control_calidad": {}})

    r = make_client(handler, ms6_url=MS6).post("/api/ruta", json=REQ)
    assert r.status_code == 200
    assert r.json()["fuente"] == "ms6"
    assert seen["url"] == f"{MS6}/route"


def test_ms6_error_4xx_se_reenvia(make_client):
    h = lambda request: httpx.Response(404, json={"detail": "Sin ruta factible"})
    r = make_client(h, ms6_url=MS6).post("/api/ruta", json=REQ)
    assert r.status_code == 404
    assert r.json() == {"detail": "Sin ruta factible"}


def test_ms6_caido_usa_fallback(make_client):
    def h(request):
        raise httpx.ConnectError("down")

    r = make_client(h, ms6_url=MS6).post("/api/ruta", json=REQ)
    assert r.status_code == 200
    assert r.json()["fuente"] == "precalculada"


def test_ms6_5xx_usa_fallback(make_client):
    h = lambda request: httpx.Response(500)
    assert make_client(h, ms6_url=MS6).post("/api/ruta", json=REQ).json()["fuente"] == "precalculada"


def test_fallback_sin_ms6_cumple_contrato(client):
    r = client.post("/api/ruta", json=REQ)
    body = r.json()
    assert r.status_code == 200 and set(body) == CONTRATO
    capas = {f["properties"]["capa"] for f in body["geojson"]["features"]}
    assert capas == {"ruta_optima", "contrafactual", "objetivo", "origen"}
    assert body["resumen"]["objetivo"] == "Oudam"
    assert body["resumen"]["dosis_rad_acum_uGy"] == 247.8
    assert len(body["tramos"]) == 13 and body["control_calidad"]["cobertura_ok"] is True


def test_fallback_todos_los_materiales(client):
    esperado = {"hematita": "Oudam", "esmectitas": "Glen Etive", "tridimita": "Buckskin"}
    for material, objetivo in esperado.items():
        assert client.post("/api/ruta", json={**REQ, "material": material}).json()["resumen"]["objetivo"] == objetivo


def test_origen_desplazado_no_usa_fallback(client):
    assert client.post("/api/ruta", json={**REQ, "lon": 137.40}).status_code == 503


def test_hora_distinta_no_usa_fallback(client):
    assert client.post("/api/ruta", json={**REQ, "hora": 14}).status_code == 503


def test_sulfatos_sin_ms6_es_503(client):
    r = client.post("/api/ruta", json={**REQ, "material": "sulfatos"})
    assert r.status_code == 503


def test_fallback_deshabilitado_es_503(make_client):
    assert make_client(precalc_fallback=False).post("/api/ruta", json=REQ).status_code == 503


def test_request_invalido_es_422(client):
    assert client.post("/api/ruta", json={**REQ, "hora": 30}).status_code == 422
    assert client.post("/api/ruta", json={**REQ, "material": "oro"}).status_code == 422
