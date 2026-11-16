"""POST /risk/evaluate — SPEC §3.1/§4.1 + additive plan fields."""

from fastapi.testclient import TestClient

from tests.conftest import GAP_PATH


def _post(client: TestClient, **overrides):  # type: ignore[no-untyped-def]
    body = {
        "body": "mars",
        "path": GAP_PATH,
        "factors": ["slope", "roughness", "dunes", "temperature", "radiation"],
        "sol": 1360,
        "hora": 9,
    }
    body.update(overrides)
    return client.post("/risk/evaluate", json=body)


def test_evaluate_happy_path(client: TestClient) -> None:
    response = _post(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["overall_risk"] is None
    assert body["risk_level"] == "unknown"
    assert body["warnings_summary"] == []
    assert body["sol"] == 1360
    assert body["hora"] == 9
    assert body["total_distance_m"] > 0
    assert len(body["segments"]) >= 1
    segment = body["segments"][0]
    assert set(segment["from"]) == {"lat", "lon"}
    assert set(segment["to"]) == {"lat", "lon"}
    assert segment["risk"] is None
    assert segment["distance_m"] > 0
    assert set(segment["factor_scores"]) == {
        "slope",
        "roughness",
        "dunes",
        "temperature",
        "radiation",
    }
    assert all(s["available"] for s in segment["factor_scores"].values())


def test_evaluate_defaults(client: TestClient) -> None:
    # factors/sol/hora/body optional per SPEC.
    response = client.post("/risk/evaluate", json={"path": GAP_PATH})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["hora"] == 12  # SPEC default
    assert body["sol"] == 1360  # RISK_DEFAULT_SOL echoed


def test_evaluate_single_point_path_is_400(client: TestClient) -> None:
    response = _post(client, path=[GAP_PATH[0]])
    assert response.status_code == 400


def test_evaluate_unknown_factor_is_400(client: TestClient) -> None:
    response = _post(client, factors=["slope", "alien"])
    assert response.status_code == 400


def test_evaluate_hora_out_of_range_is_400(client: TestClient) -> None:
    response = _post(client, hora=24)
    assert response.status_code == 400


def test_evaluate_unknown_vehicle_profile_is_404(client: TestClient) -> None:
    response = _post(client, vehicle_profile="warp_drive")
    assert response.status_code == 404
    assert "VEHICLE_PROFILE_NOT_FOUND" in response.json()["detail"]


def test_evaluate_bad_sampling_step_is_400(client: TestClient) -> None:
    response = _post(client, sampling_step_m=0)
    assert response.status_code == 400


def test_evaluate_off_grid_is_404(client: TestClient) -> None:
    response = _post(
        client,
        path=[{"lat": 0.0, "lon": 0.0}, {"lat": 0.01, "lon": 0.01}],
    )
    assert response.status_code == 404


def test_evaluate_factor_subset(client: TestClient) -> None:
    response = _post(client, factors=["slope"])
    assert response.status_code == 200
    segment = response.json()["segments"][0]
    assert set(segment["factor_scores"]) == {"slope"}


def test_evaluate_nearest_sol_echoed(client: TestClient) -> None:
    # sol=5000 -> nearest RAD sol 4710, nearest REMS sol 2140.
    response = _post(client, sol=5000, hora=3)
    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert provenance["reference_sol"] == 5000
    assert provenance["rems_sol"] == 2140
    assert provenance["rad_sol"] == 4710


def test_evaluate_missing_path_is_422(client: TestClient) -> None:
    response = client.post("/risk/evaluate", json={"body": "mars"})
    assert response.status_code == 422
