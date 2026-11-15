import os

import pytest

MS6 = os.environ.get("CORE_E2E_MS6_URL", "")
pytestmark = pytest.mark.skipif(not MS6, reason="define CORE_E2E_MS6_URL para probar contra un MS6 real")

REQ = {"lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9.0, "vmax": 1000}


@pytest.fixture
def e2e(make_client):
    return make_client(ms6_url=MS6, precalc_fallback=False)


def test_ruta_real_cumple_contrato(e2e):
    r = e2e.post("/api/ruta", json=REQ)
    body = r.json()
    assert r.status_code == 200 and body["fuente"] == "ms6"
    assert {"geojson", "resumen", "tramos", "control_calidad"} <= set(body)
    capas = {f["properties"]["capa"] for f in body["geojson"]["features"]}
    assert capas == {"ruta_optima", "contrafactual", "objetivo", "origen"}


def test_ruta_real_coincide_con_precalculada(e2e, make_client):
    real = e2e.post("/api/ruta", json=REQ).json()["resumen"]
    pre = make_client(ms6_url="").post("/api/ruta", json=REQ).json()["resumen"]
    assert real.keys() == pre.keys()
    assert real["objetivo"] == pre["objetivo"]
    assert real["distancia_km"] == pre["distancia_km"]
    assert real["dosis_rad_acum_uGy"] == pre["dosis_rad_acum_uGy"]


def test_sulfatos_solo_funciona_con_ms6(e2e):
    assert e2e.post("/api/ruta", json={**REQ, "material": "sulfatos"}).status_code in (200, 404)


def test_hora_distinta_calcula_ruta_nueva(e2e):
    r = e2e.post("/api/ruta", json={**REQ, "hora": 14})
    assert r.status_code == 200 and r.json()["fuente"] == "ms6"


def test_error_4xx_de_ms6_se_reenvia(e2e):
    assert e2e.post("/api/ruta", json={**REQ, "sol": 999}).status_code == 400
    assert e2e.post("/api/ruta", json={**REQ, "lon": 10.0}).status_code == 400
