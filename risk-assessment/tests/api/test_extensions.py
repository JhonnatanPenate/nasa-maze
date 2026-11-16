"""Plan-extension endpoints: vehicle-profiles, meta, area (additive stubs)."""

from fastapi.testclient import TestClient


def test_vehicle_profiles(client: TestClient) -> None:
    response = client.get("/risk/vehicle-profiles")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["default"] == "baseline_mars_rover"
    names = [p["name"] for p in body["profiles"]]
    assert "baseline_mars_rover" in names
    profile = body["profiles"][0]
    assert "slope_block_deg" in profile
    assert "dose_budget_uGy" in profile


def test_meta(client: TestClient) -> None:
    response = client.get("/risk/meta")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["service"] == "risk-assessment"
    assert body["model_version"]
    assert body["weights"]["slope"] == 0.4
    assert body["thresholds"]["levels"]["high_max"] == 0.75
    assert body["default_sol"] == 1360
    assert body["datasource_mode"] == "synthetic"
    assert body["upstream"] == {
        "terrain": "ok",
        "raster": "ok",
        "environment": "ok",
    }
    assert body["catalog"]["available"] is False  # no catalog file yet
    assert body["coordinate_system"]["crs"] == "IAU_2015:49900"


def test_area_stub_validates_and_caps(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={
            "bbox": [137.345, -4.740, 137.455, -4.580],
            "sol": 1360,
            "hora": 12,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["aggregation"] == "pending"
    assert body["cell_count"] > 0
    assert body["mean_score"] is None


def test_area_too_large_is_422(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={
            "bbox": [137.345, -4.740, 137.455, -4.580],
            "max_cells": 10,
        },
    )
    assert response.status_code == 422
    assert "AREA_TOO_LARGE" in response.json()["detail"]


def test_area_bad_bbox_is_400(client: TestClient) -> None:
    # min_lat=200 is outside [-90, 90] -> DomainValidationError -> 400.
    response = client.post("/risk/area", json={"bbox": [1, 200, 3, 4]})
    assert response.status_code == 400


def test_area_bad_hora_is_400(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={"bbox": [137.3, -4.8, 137.5, -4.5], "hora": 99},
    )
    assert response.status_code == 400
