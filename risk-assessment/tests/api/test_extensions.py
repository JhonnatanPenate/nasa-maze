"""Plan-extension endpoints: vehicle-profiles, meta, area (additive)."""

import pytest
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
    # Phase 2 ships a real catalog (data/processed or the committed seed).
    assert body["catalog"]["available"] is True
    assert body["catalog"]["rems_sols"] == [1360, 2140]
    assert body["catalog"]["rad_sols"] == [1360, 2140, 3290, 4710]
    assert body["coordinate_system"]["crs"] == "IAU_2015:49900"


def test_area_aggregates_grid_cells(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={
            "bbox": [137.36, -4.65, 137.44, -4.60],
            "sol": 1360,
            "hora": 12,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["aggregation"] == "grid_cells"
    assert body["cell_count"] > 0
    assert body["cell_size_m"] == pytest.approx(90.0, abs=5.0)
    level_counts = body["level_counts"]
    assert set(level_counts) == {"low", "medium", "high", "critical", "unknown"}
    assert sum(level_counts.values()) == body["cell_count"]
    assert body["mean_score"] is not None
    assert 0.0 <= body["mean_score"] <= 1.0
    assert body["p95_score"] is not None
    assert body["blocked_fraction"] is not None
    assert 0.0 <= body["blocked_fraction"] <= 1.0
    assert set(body["factor_stats"]) == {
        "slope",
        "roughness",
        "dunes",
        "temperature",
        "radiation",
    }
    assert body["confidence"] == "high"
    assert body["uncovered_cells"] == 0
    assert body["provenance"]["vehicle_profile"] == "baseline_mars_rover"
    # Statistics only — never a per-cell raster.
    assert "cells" not in body and "grid" not in body


def test_area_outside_coverage_is_unknown(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={"bbox": [10.0, -20.0, 10.02, -19.98]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["level_counts"]["unknown"] == body["cell_count"]
    assert body["uncovered_cells"] == body["cell_count"]
    assert body["mean_score"] is None
    assert body["blocked_fraction"] is None
    assert body["confidence"] == "low"


def test_area_unknown_vehicle_profile_is_404(client: TestClient) -> None:
    response = client.post(
        "/risk/area",
        json={
            "bbox": [137.36, -4.65, 137.44, -4.60],
            "vehicle_profile": "no_such_rover",
        },
    )
    assert response.status_code == 404
    assert "VEHICLE_PROFILE_NOT_FOUND" in response.json()["detail"]


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
