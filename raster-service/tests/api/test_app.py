from fastapi.testclient import TestClient

from app.composition.dependencies import get_repository
from app.core.ports.raster_repository import RasterRepository
from app.main import create_app
from tests.conftest import TEST_DATASET

# Smoke tests over the assembled create_app(): every registered route
# answers a valid request (none 404), and the OpenAPI path list exposes
# the full MS3 contract. Test grid: dataset "test", extent lon
# 137.40..137.48, lat -4.70..-4.60; bands slope_deg, roughness_m,
# dark_fraction.


def test_health_route_registered(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_datasets_route_registered(client: TestClient):
    response = client.get("/raster/datasets")

    assert response.status_code == 200
    assert response.json()["datasets"][0]["name"] == TEST_DATASET


def test_metadata_route_registered(client: TestClient):
    response = client.get(f"/raster/{TEST_DATASET}/metadata")

    assert response.status_code == 200
    assert response.json()["name"] == TEST_DATASET


def test_point_route_registered(client: TestClient):
    response = client.get(
        f"/raster/{TEST_DATASET}/point",
        params={"lat": -4.615, "lon": 137.415},
    )

    assert response.status_code == 200
    assert "values" in response.json()


def test_window_route_registered(client: TestClient):
    response = client.post(
        f"/raster/{TEST_DATASET}/window",
        json={
            "band": "slope_deg",
            "bbox": [137.41, -4.62, 137.43, -4.61],
        },
    )

    assert response.status_code == 200
    assert "cells" in response.json()


def test_sample_route_registered(client: TestClient):
    response = client.post(
        f"/raster/{TEST_DATASET}/sample",
        json={
            "band": "slope_deg",
            "path": [
                {"lat": -4.605, "lon": 137.405},
                {"lat": -4.615, "lon": 137.405},
            ],
        },
    )

    assert response.status_code == 200
    assert "samples" in response.json()


def test_layer_route_registered(client: TestClient):
    response = client.get(f"/raster/{TEST_DATASET}/layer/slope_deg")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


class _ExplodingRepository(RasterRepository):
    """Repository whose calls raise non-service exceptions."""

    def dataset_names(self):
        return ["boom"]

    def metadata(self, dataset):
        raise RuntimeError("kaboom")

    def read_cells(self, dataset, band, rows, cols):
        raise RuntimeError("kaboom")

    def is_readable(self, dataset):
        return False


def test_unexpected_error_is_500_internal_error():
    app = create_app()
    app.dependency_overrides[get_repository] = _ExplodingRepository
    # ServerErrorMiddleware re-raises after sending the 500 response so
    # the server still logs the traceback; disable client-side re-raise.
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/raster/boom/point", params={"lat": -4.6, "lon": 137.4}
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "internal error"}
    assert "kaboom" not in response.text


def test_openapi_lists_all_seven_endpoints(client: TestClient):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/health",
        "/raster/datasets",
        "/raster/{dataset}/metadata",
        "/raster/{dataset}/point",
        "/raster/{dataset}/window",
        "/raster/{dataset}/sample",
        "/raster/{dataset}/layer/{band}",
    ):
        assert path in paths, f"{path} missing from OpenAPI"
