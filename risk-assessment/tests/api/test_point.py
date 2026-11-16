"""GET /risk/point — SPEC §3.2/§4.2 + additive params."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import GAP_POINT, OFF_GRID_POINT


def test_point_happy_path(client: TestClient) -> None:
    response = client.get("/risk/point", params={**GAP_POINT, "sol": 1360, "hora": 9})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lat"] == GAP_POINT["lat"]
    assert body["lon"] == GAP_POINT["lon"]
    # Phase 4: real weighted score from the domain scorers.
    assert body["risk"] is not None
    assert 0.0 <= body["risk"] <= 1.0
    assert body["risk_level"] in {"low", "medium", "high", "critical", "unknown"}
    assert set(body["factor_scores"]) == {
        "slope",
        "roughness",
        "dunes",
        "temperature",
        "radiation",
    }
    for entry in body["factor_scores"].values():
        assert entry["score"] is not None
        assert 0.0 <= entry["score"] <= 1.0
        assert entry["available"] is True
    assert body["confidence"] in {"high", "medium", "low"}
    assert body["assumptions"]
    assert body["sol"] == 1360
    assert body["hora"] == 9
    assert body["provenance"]["rems_sol"] == 1360
    assert body["provenance"]["rad_sol"] == 1360
    assert body["provenance"]["scoring"] == "ms5-risk-v0.1"


def test_point_factor_subset(client: TestClient) -> None:
    response = client.get(
        "/risk/point",
        params={**GAP_POINT, "factors": "slope,temperature"},
    )
    assert response.status_code == 200
    assert set(response.json()["factor_scores"]) == {"slope", "temperature"}


def test_point_unknown_factor_is_400(client: TestClient) -> None:
    response = client.get("/risk/point", params={**GAP_POINT, "factors": "slope,magical"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_point_invalid_hora_is_400(client: TestClient) -> None:
    response = client.get("/risk/point", params={**GAP_POINT, "hora": 25})
    assert response.status_code == 400


def test_point_out_of_coverage_is_404(client: TestClient) -> None:
    response = client.get("/risk/point", params=OFF_GRID_POINT)
    assert response.status_code == 404
    assert "detail" in response.json()


def test_point_invalid_coordinates_is_400(client: TestClient) -> None:
    response = client.get("/risk/point", params={"lat": 95.0, "lon": 0.0})
    assert response.status_code == 400


def test_point_omitted_hora_returns_worst_and_hourly(client: TestClient) -> None:
    response = client.get("/risk/point", params={**GAP_POINT, "include_hourly": "true"})
    assert response.status_code == 200
    body = response.json()
    assert body["hora"] is not None
    assert len(body["by_hour"]) == 24
    for hourly in body["by_hour"]:
        # Fake catalog has uniform profiles -> every hour scores the same.
        assert hourly["risk"] is not None
        assert 0.0 <= hourly["risk"] <= 1.0
        assert hourly["risk_level"] in {"low", "medium", "high", "critical", "unknown"}


def test_point_no_environment_still_answers(client: TestClient, app) -> None:  # type: ignore[no-untyped-def]
    from app.composition import dependencies

    from tests.fakes.fake_environment_repository import FakeEnvironmentRepository

    app.dependency_overrides[dependencies.get_environment_repository] = lambda: (
        FakeEnvironmentRepository()
    )
    response = client.get("/risk/point", params={**GAP_POINT, "hora": 9})
    assert response.status_code == 200
    body = response.json()
    scores = body["factor_scores"]
    assert scores["slope"]["available"] is True  # MS4 synthetic still up
    assert scores["slope"]["score"] is not None
    assert scores["temperature"]["available"] is False
    assert scores["temperature"]["score"] is None
    assert scores["radiation"]["available"] is False
    assert scores["radiation"]["score"] is None
    # Terrain/raster factors still score -> real risk, not unknown.
    assert body["risk"] is not None
    assert body["risk_level"] != "unknown"
    # Missing environmental coverage is reported, not hidden.
    assert any("unavailable" in note for note in body["data_quality_notes"])


@pytest.mark.parametrize("missing", ["lat", "lon"])
def test_point_missing_param_is_422(client: TestClient, missing: str) -> None:
    params = {k: v for k, v in GAP_POINT.items() if k != missing}
    response = client.get("/risk/point", params=params)
    assert response.status_code == 422
