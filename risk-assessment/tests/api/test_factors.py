"""GET /risk/factors — SPEC §3.3 catalog + coverage."""

from fastapi.testclient import TestClient


def test_factors_catalog(client: TestClient) -> None:
    response = client.get("/risk/factors")
    assert response.status_code == 200, response.text
    body = response.json()
    ids = [f["id"] for f in body["factors"]]
    assert ids == ["slope", "roughness", "dunes", "temperature", "radiation"]
    for factor in body["factors"]:
        assert factor["available"] is True
        assert factor["weight"] > 0
        assert factor["sources"]
    assert body["weights"] == {
        "slope": 0.4,
        "dunes": 0.2,
        "roughness": 0.15,
        "temperature": 0.15,
        "radiation": 0.1,
    }
    assert body["model_version"]
    assert body["default_sol"] == 1360
    assert body["environmental_sols"]["rems"] == [1360, 2140]
    assert body["environmental_sols"]["rad"] == [1360, 2140, 3290, 4710]


def test_factors_degraded_without_upstreams(app, client) -> None:  # type: ignore[no-untyped-def]
    # Point every datasource at unavailable adapters.
    from app.composition import dependencies
    from app.infrastructure.datasources.unavailable_sources import (
        UnavailableRasterSource,
        UnavailableTerrainSource,
    )

    from tests.fakes.fake_environment_repository import FakeEnvironmentRepository

    app.dependency_overrides[dependencies.get_terrain_source] = lambda: UnavailableTerrainSource(
        "test"
    )
    app.dependency_overrides[dependencies.get_raster_source] = lambda: UnavailableRasterSource(
        "test"
    )
    app.dependency_overrides[dependencies.get_environment_repository] = lambda: (
        FakeEnvironmentRepository()
    )
    response = client.get("/risk/factors")
    assert response.status_code == 200
    body = response.json()
    assert all(f["available"] is False for f in body["factors"])
    assert body["environmental_sols"] == {"rems": [], "rad": []}
