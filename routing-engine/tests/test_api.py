from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BRADBURY = {"lon": 137.4416, "lat": -4.5895, "material": "hematita", "sol": 1360, "hora": 9.0}


def test_health():
    assert client.get("/health").status_code == 200


def test_material_invalido_422():
    assert client.post("/route", json={**BRADBURY, "material": "oro"}).status_code == 422


def test_fuera_del_aoi_400():
    assert client.post("/route", json={**BRADBURY, "lon": 137.5}).status_code == 400


def test_sol_invalido_400():
    assert client.post("/route", json={**BRADBURY, "sol": 1000}).status_code == 400


def test_ruta_hematita_desde_bradbury():
    # valor de referencia: docs/data/EJEMPLO_API_RESPUESTA.json
    r = client.post("/route", json=BRADBURY)
    assert r.status_code == 200
    body = r.json()
    assert abs(body["resumen"]["dosis_rad_acum_uGy"] - 247.8) < 0.1
    assert body["resumen"]["objetivo"] == "Oudam"
    assert body["geojson"]["crs"]["properties"]["name"] == "IAU_2015:49900"
    assert {f["properties"]["capa"] for f in body["geojson"]["features"]} == {
        "ruta_optima", "contrafactual", "objetivo", "origen"}
    assert body["tramos"][-1]["dosis_acumulada_uGy"] == body["resumen"]["dosis_rad_acum_uGy"]
