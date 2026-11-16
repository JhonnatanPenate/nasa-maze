"""Shared error contract: {"detail": ...} + SPEC status mapping."""

from app.composition import dependencies
from fastapi.testclient import TestClient

from tests.conftest import GAP_PATH, GAP_POINT
from tests.fakes.failing_sources import FailingRasterSource, FailingTerrainSource


def test_400_body_is_detail_string(client: TestClient) -> None:
    response = client.get("/risk/point", params={**GAP_POINT, "hora": 99})
    assert response.status_code == 400
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["detail"]


def test_404_body_is_detail_string(client: TestClient) -> None:
    response = client.post(
        "/risk/evaluate",
        json={"path": [{"lat": 0.0, "lon": 0.0}, {"lat": 0.01, "lon": 0.01}]},
    )
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_502_when_terrain_upstream_down(app, client) -> None:  # type: ignore[no-untyped-def]
    app.dependency_overrides[dependencies.get_terrain_source] = lambda: FailingTerrainSource()
    response = client.post("/risk/evaluate", json={"path": GAP_PATH})
    assert response.status_code == 502
    assert isinstance(response.json()["detail"], str)


def test_502_when_raster_upstream_down(app, client) -> None:  # type: ignore[no-untyped-def]
    app.dependency_overrides[dependencies.get_raster_source] = lambda: FailingRasterSource()
    response = client.get("/risk/point", params=GAP_POINT)
    assert response.status_code == 502


def test_unexpected_error_is_sanitized_500(app) -> None:  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    def boom() -> None:
        raise RuntimeError("secret internals")

    app.dependency_overrides[dependencies.get_settings] = boom  # type: ignore[assignment]
    # raise_server_exceptions=False: ServerErrorMiddleware re-raises after
    # sending the sanitized 500 so the server can log it.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"].startswith("INTERNAL_ERROR")
    assert "secret internals" not in body["detail"]
