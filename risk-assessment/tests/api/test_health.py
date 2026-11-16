"""GET /health — liveness + upstream status (SPEC §6)."""

from app.composition import dependencies
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.fakes.fake_environment_repository import FakeEnvironmentRepository


def test_health_ok_with_full_coverage(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["datasource_mode"] == "synthetic"
    assert body["terrain"] == "ok"
    assert body["raster"] == "ok"
    assert body["environment"] == "ok"


def test_health_degraded_without_environment(app: FastAPI, client: TestClient) -> None:
    # Override the env repo with an empty one -> temperature/radiation down.
    app.dependency_overrides[dependencies.get_environment_repository] = lambda: (
        FakeEnvironmentRepository()
    )
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["environment"] == "unavailable"
