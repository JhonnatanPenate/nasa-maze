"""POST /risk/evaluate — SPEC §3.1/§4.1 + additive plan fields."""

import time

import pytest
from app.composition import dependencies
from fastapi.testclient import TestClient

from tests.conftest import GAP_PATH, full_environment

# ~5.05 km inside the synthetic coverage -> ~57 segments at 90 m.
LONG_PATH = [
    {"lat": -4.60, "lon": 137.36},
    {"lat": -4.63, "lon": 137.44},
]


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
    # Phase 4: real weighted scores, never fabricated.
    assert body["overall_risk"] is not None
    assert 0.0 <= body["overall_risk"] <= 1.0
    assert body["risk_level"] in {"low", "medium", "high", "critical", "unknown"}
    assert body["warnings_summary"]
    assert body["sol"] == 1360
    assert body["hora"] == 9
    assert body["total_distance_m"] > 0
    # Additive plan fields (plan §7.2).
    assert body["max_level"] in {"low", "medium", "high", "critical", "unknown"}
    assert body["mean_score"] is not None
    assert body["p95_score"] is not None
    assert body["dominant_factor"] in {
        "slope",
        "roughness",
        "dunes",
        "temperature",
        "radiation",
    }
    assert body["total_duration_s"] > 0
    assert 0 <= body["end_local_time_hours"] < 24
    assert body["confidence"] in {"high", "medium", "low"}
    assert body["provenance"]["vehicle_profile"] == "baseline_mars_rover"
    assert isinstance(body["restrictions"], list)
    assert isinstance(body["hotspots"], list)
    assert isinstance(body["blocking_segments"], list)
    assert len(body["segments"]) >= 1
    segment = body["segments"][0]
    assert set(segment["from"]) == {"lat", "lon"}
    assert set(segment["to"]) == {"lat", "lon"}
    assert segment["risk"] is not None
    assert 0.0 <= segment["risk"] <= 1.0
    assert segment["distance_m"] > 0
    assert 0 <= segment["local_time_hour"] <= 23
    assert set(segment["factor_scores"]) == {
        "slope",
        "roughness",
        "dunes",
        "temperature",
        "radiation",
    }
    for entry in segment["factor_scores"].values():
        assert entry["available"] is True
        assert entry["score"] is not None
        assert 0.0 <= entry["score"] <= 1.0


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


# --- Phase 4: scoring wiring, LMST advance, additive plan fields ---------


def test_evaluate_overall_is_distance_weighted_mean(client: TestClient) -> None:
    body = _post(client).json()
    numerator = 0.0
    denominator = 0.0
    for segment in body["segments"]:
        if segment["risk"] is not None and segment["distance_m"] > 0:
            numerator += segment["risk"] * segment["distance_m"]
            denominator += segment["distance_m"]
    assert body["overall_risk"] == pytest.approx(numerator / denominator)


def test_evaluate_lmst_advances_and_wraps(client: TestClient) -> None:
    # 72 m/h override -> 1.25 h per 90 m segment -> ~45 h over the path,
    # so the 24-bin LMST clock must wrap past departure hour 9.
    response = _post(client, speed_mps=0.02, hora=9)
    assert response.status_code == 200, response.text
    body = response.json()
    hours = [s["local_time_hour"] for s in body["segments"]]
    assert all(0 <= h <= 23 for h in hours)
    assert min(hours) < 9  # wrapped past midnight LMST
    expected_end = (9 + body["total_duration_s"] / 3600.0) % 24
    assert body["end_local_time_hours"] == pytest.approx(expected_end, abs=1e-6)


def test_evaluate_speed_override_changes_duration(client: TestClient) -> None:
    default_body = _post(client).json()
    fast_body = _post(client, speed_mps=10.0).json()  # 36 km/h -> ~324 s
    assert fast_body["total_duration_s"] < default_body["total_duration_s"] / 10


def test_evaluate_no_cumulative_dose_anywhere(client: TestClient) -> None:
    """MS5 reports radiation as a per-segment rate only; route dose
    accumulation belongs to MS6 (SPEC §8 / plan §7.1)."""
    body = _post(client).json()

    def keys(node: object) -> list[str]:
        if isinstance(node, dict):
            return [str(k) for k in node] + [
                key for v in node.values() for key in keys(v)
            ]
        if isinstance(node, list):
            return [key for v in node for key in keys(v)]
        return []

    assert not any("dose" in k.lower() for k in keys(body))


def test_evaluate_restrictions_with_factor_subset(client: TestClient) -> None:
    """Restrictions are additive: they are evaluated even when ``factors``
    selects a terrain-only subset (slope/soil/tilt inputs are always
    fetched for path evaluation)."""
    response = _post(client, factors=["slope"])
    assert response.status_code == 200, response.text
    body = response.json()
    segment = body["segments"][0]
    assert set(segment["factor_scores"]) == {"slope"}
    assert body["restrictions"]  # steep synthetic terrain -> SLOPE_BLOCK
    assert any(r["code"] == "SLOPE_BLOCK" for r in body["restrictions"])
    assert all(
        r["code"]
        in {"SLOPE_BLOCK", "TILT_BLOCK", "TILT_MARGIN_BLOCK", "THERMAL_OUT_OF_BAND"}
        for r in body["restrictions"]
    )
    assert body["blocking_segments"]
    # Restrictions never alter the SPEC weighted score.
    assert segment["risk"] == pytest.approx(
        segment["factor_scores"]["slope"]["score"]
    )


def test_evaluate_synthetic_deterministic(client: TestClient) -> None:
    first = _post(client).json()
    second = _post(client).json()
    assert first == second


def test_evaluate_perf_50_segments_under_3s(client: TestClient) -> None:
    """SPEC §6 NFR: 50-segment path evaluation under 3 seconds."""
    started = time.perf_counter()
    response = _post(client, path=LONG_PATH)
    elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["segments"]) >= 50
    assert elapsed < 3.0


def test_evaluate_bad_speed_is_400(client: TestClient) -> None:
    response = _post(client, speed_mps=0)
    assert response.status_code == 400


def test_evaluate_too_many_points_is_400(client: TestClient) -> None:
    response = _post(client, path=[GAP_PATH[0]] * 1001)
    assert response.status_code == 400


def test_evaluate_upstream_count_mismatch_is_502(app, client) -> None:  # type: ignore[no-untyped-def]
    """MS3/MS4 sample lists that don't align with the path sampling are an
    upstream contract violation -> 502, never a fabricated score."""

    class ShortRasterSource:
        def ping(self) -> bool:
            return True

        def dataset_bands(self) -> tuple[str, ...]:
            return ()

        def point_values(self, point):  # type: ignore[no-untyped-def]
            return {}

        def sample_band(self, band, path, sample_distance_m):  # type: ignore[no-untyped-def]
            return ()  # wrong count on purpose

    app.dependency_overrides[dependencies.get_raster_source] = lambda: ShortRasterSource()
    response = _post(client)
    assert response.status_code == 502
    assert "detail" in response.json()


def test_evaluate_rad_fallback_marked_in_data_quality_notes(app, client) -> None:  # type: ignore[no-untyped-def]
    app.dependency_overrides[dependencies.get_environment_repository] = lambda: (
        full_environment(rad_provenance="sol_mean_fallback")
    )
    response = _post(client)
    assert response.status_code == 200, response.text
    notes = response.json()["data_quality_notes"]
    assert any("sol-mean hourly fallback" in note for note in notes)
