import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.main import create_app

# Real-data contract test against the delivered raster
# data/gale/processed/rejilla_ruta_90m.tif (ground truth: plan §1.1).
# Uses create_app() with the real default Settings — no overrides.

REJILLA_PATH = Path(Settings().rejilla_path)

pytestmark = pytest.mark.skipif(
    not REJILLA_PATH.exists(),
    reason=f"delivered raster not present: {REJILLA_PATH}",
)

EXPECTED_BAND_NAMES = [
    "pendiente_grados",
    "rugosidad_m",
    "fraccion_oscura",
    "inercia_termica_tiu",
    "albedo",
    "distancia_duna_m",
]
EXPECTED_BOUNDS = [137.345, -4.739427215909189, 137.45432151948057, -4.58]
EXPECTED_RESOLUTION_DEG = 0.0015183544372303697


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_metadata_matches_delivered_file(client: TestClient):
    response = client.get("/raster/rejilla/metadata")

    assert response.status_code == 200
    body = response.json()
    assert body["crs"] == "IAU_2015:49900"
    assert body["width"] == 72
    assert body["height"] == 105
    assert body["bounds"] == pytest.approx(EXPECTED_BOUNDS)
    assert body["resolution_deg"]["lon"] == pytest.approx(
        EXPECTED_RESOLUTION_DEG
    )
    assert body["resolution_deg"]["lat"] == pytest.approx(
        EXPECTED_RESOLUTION_DEG
    )
    assert [band["name"] for band in body["bands"]] == EXPECTED_BAND_NAMES


def test_fraccion_oscura_full_window_has_exactly_one_null(
    client: TestClient,
):
    response = client.post(
        "/raster/rejilla/window",
        json={"band": "fraccion_oscura", "bbox": EXPECTED_BOUNDS},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 105
    assert body["cols"] == 72
    nulls = sum(
        1 for row in body["cells"] for value in row if value is None
    )
    assert nulls == 1


def test_point_inside_extent_returns_six_values(client: TestClient):
    response = client.get(
        "/raster/rejilla/point",
        params={"lat": -4.5895, "lon": 137.4416},
    )

    assert response.status_code == 200
    values = response.json()["values"]
    assert list(values) == EXPECTED_BAND_NAMES


def test_layer_returns_png_one_pixel_per_cell(client: TestClient):
    response = client.get("/raster/rejilla/layer/pendiente_grados")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    png = response.content
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert png[12:16] == b"IHDR"
    width, height = struct.unpack(">II", png[16:24])
    assert (width, height) == (72, 105)
