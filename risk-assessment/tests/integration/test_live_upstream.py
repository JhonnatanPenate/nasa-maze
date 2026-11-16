"""Live-upstream parity checks — skipped unless MS3 :8003 and MS4 :8004
are reachable (same pattern as MS4's integration tests)."""

import socket

import pytest
from app.composition import dependencies
from app.infrastructure.datasources.http_raster_source import HttpRasterSource
from app.infrastructure.datasources.http_terrain_source import HttpTerrainSource
from fastapi.testclient import TestClient

from tests.conftest import GAP_PATH, GAP_POINT, reset_singletons


def _reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


MS3_UP = _reachable("localhost", 8003)
MS4_UP = _reachable("localhost", 8004)

pytestmark = pytest.mark.skipif(not (MS3_UP and MS4_UP), reason="MS3/MS4 not reachable")


@pytest.fixture
def http_client(app, monkeypatch):  # type: ignore[no-untyped-def]
    """App wired to live MS3/MS4 via dependency overrides."""
    import httpx

    monkeypatch.setenv("RISK_DATASOURCE_MODE", "http")
    reset_singletons()
    raster = HttpRasterSource(httpx.Client(base_url="http://localhost:8003"), "rejilla", retries=1)
    terrain = HttpTerrainSource(httpx.Client(base_url="http://localhost:8004"), "mars", retries=1)
    app.dependency_overrides[dependencies.get_raster_source] = lambda: raster
    app.dependency_overrides[dependencies.get_terrain_source] = lambda: terrain
    with TestClient(app) as client:
        yield client


def test_live_health(http_client: TestClient) -> None:
    body = http_client.get("/health").json()
    assert body["terrain"] == "ok"
    assert body["raster"] == "ok"


def test_live_point(http_client: TestClient) -> None:
    response = http_client.get("/risk/point", params={**GAP_POINT, "hora": 12})
    assert response.status_code == 200, response.text
    scores = response.json()["factor_scores"]
    # slope comes from MS4, roughness/dunes from MS3 — real coverage expected.
    assert scores["slope"]["available"] is True
    assert scores["roughness"]["available"] is True


def test_live_evaluate(http_client: TestClient) -> None:
    response = http_client.post("/risk/evaluate", json={"path": GAP_PATH})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["segments"]) >= 1
    assert body["overall_risk"] is None  # scores pending Phase 3
    assert body["risk_level"] == "unknown"
