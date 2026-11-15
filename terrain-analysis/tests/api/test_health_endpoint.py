import pytest

from app.features.health.presentation.health_router import router

EXPECTED_KEYS = {"status", "datasource", "datasource_kind"}


@pytest.fixture
def client(make_client):
    return make_client(router)


@pytest.fixture
def failing_client(make_failing_client):
    return make_failing_client(router)


def test_health_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == EXPECTED_KEYS
    assert payload == {
        "status": "ok",
        "datasource": "ok",
        "datasource_kind": "synthetic",
    }


def test_health_degraded_when_datasource_fails(failing_client) -> None:
    response = failing_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == EXPECTED_KEYS
    assert payload == {
        "status": "degraded",
        "datasource": "unavailable",
        "datasource_kind": "synthetic",
    }
