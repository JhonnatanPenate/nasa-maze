import io

from PIL import Image

from app.datasources.raster_layers import BANDAS


def test_capas_base(client):
    r = client.get("/api/capas/base")
    assert r.status_code == 200
    body = r.json()
    capas = [f["properties"]["capa"] for f in body["features"]]
    assert capas.count("puntos_quimica") == 21
    assert capas.count("traza_msl") == 1 and capas.count("origen") == 1
    assert body["crs"]["properties"]["name"] == "IAU_2015:49900"


def test_capas_base_preserva_columnas_y_nulos(client):
    puntos = [f for f in client.get("/api/capas/base").json()["features"] if f["properties"]["capa"] == "puntos_quimica"]
    rocknest = next(f for f in puntos if f["properties"]["nombre"] == "Rocknest")
    assert rocknest["properties"]["hematita_pct"] is None
    assert rocknest["geometry"]["coordinates"] == [137.4483, -4.59]


def test_capas_base_datos_faltantes_es_502(make_client, tmp_path):
    r = make_client(data_dir=str(tmp_path)).get("/api/capas/base")
    assert r.status_code == 502


def test_raster_todas_las_bandas(client):
    for banda in BANDAS:
        r = client.get(f"/api/capas/raster/{banda}")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        img = Image.open(io.BytesIO(r.content))
        assert img.mode == "RGBA" and img.size == (72, 105)
        assert len(r.headers["x-bounds"].split(",")) == 4


def test_raster_gray(client):
    r = client.get("/api/capas/raster/albedo", params={"cmap": "gray"})
    assert r.status_code == 200


def test_raster_banda_invalida_es_422(client):
    assert client.get("/api/capas/raster/elevacion").status_code == 422
    assert client.get("/api/capas/raster/albedo", params={"cmap": "jet"}).status_code == 422


def test_raster_datos_faltantes_es_502(make_client, tmp_path):
    assert make_client(data_dir=str(tmp_path)).get("/api/capas/raster/albedo").status_code == 502


def test_modelos(client):
    r = client.get("/api/modelos")
    assert r.status_code == 200
    assert {"parametros", "resumen", "reglas_suelo"} <= set(r.json())


def test_modelos_faltante_es_502(make_client, tmp_path):
    assert make_client(data_dir=str(tmp_path)).get("/api/modelos").status_code == 502
