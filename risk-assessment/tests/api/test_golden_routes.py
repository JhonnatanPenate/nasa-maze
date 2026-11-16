"""Golden-route validation (plan Phase 5, plan §10).

Runs the three delivered science routes — ``ruta_esmectitas``,
``ruta_hematita``, ``ruta_tridimita`` — through ``POST /risk/evaluate`` in
synthetic mode and asserts:

- deterministic output (two identical calls),
- ``total_distance_m`` matches ``ruta_*_resumen.json`` ``distancia_km``
  and the ``ruta_*_tramos.xlsx`` ``distancia_m`` column sums within
  tolerance (fixtures in ``tests/fixtures/golden_routes.json``),
- structural sanity: SPEC factor scores present, valid levels, no
  route-dose field (dose accumulation belongs to MS6).

Per-segment soil/slope/dose values are NOT compared: in synthetic mode
MS3/MS4 return deterministic stand-ins, not the delivered raster — the
tramos comparison is limited to distance (non-contractual sanity).
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "golden_routes.json"
GOLDEN_ROUTES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

# Geodesic distance along the delivered cell-centre polyline vs Javi's
# grid-step bookkeeping: observed deviation < 0.2%; 2% is a safe bound.
DISTANCE_TOLERANCE = 0.02
SPEC_FACTORS = {"slope", "roughness", "dunes", "temperature", "radiation"}
VALID_LEVELS = {"low", "medium", "high", "critical", "unknown"}


def _evaluate(client: TestClient, route: dict) -> dict:
    response = client.post(
        "/risk/evaluate",
        json={"path": route["path"], "sol": route["sol"], "hora": route["hora"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("route_name", sorted(GOLDEN_ROUTES))
def test_golden_route_runs_and_is_deterministic(
    client: TestClient, route_name: str
) -> None:
    route = GOLDEN_ROUTES[route_name]
    first = _evaluate(client, route)
    second = _evaluate(client, route)
    assert first == second
    assert len(first["segments"]) >= 2


@pytest.mark.parametrize("route_name", sorted(GOLDEN_ROUTES))
def test_golden_route_distance_matches_resumen_and_tramos(
    client: TestClient, route_name: str
) -> None:
    route = GOLDEN_ROUTES[route_name]
    body = _evaluate(client, route)
    total_m = body["total_distance_m"]

    expected_resumen_m = route["expected_distance_km"] * 1000.0
    assert total_m == pytest.approx(expected_resumen_m, rel=DISTANCE_TOLERANCE)

    # Non-contractual sanity vs _tramos.xlsx distancia_m column sums.
    assert total_m == pytest.approx(route["tramos_distance_m"], rel=DISTANCE_TOLERANCE)

    # Segment pitch sanity: ~sampling_step_m arc-length intervals.
    n_segments = len(body["segments"])
    assert n_segments == pytest.approx(total_m / 90.0, rel=0.15)


@pytest.mark.parametrize("route_name", sorted(GOLDEN_ROUTES))
def test_golden_route_response_sanity(client: TestClient, route_name: str) -> None:
    body = _evaluate(client, GOLDEN_ROUTES[route_name])

    assert body["risk_level"] in VALID_LEVELS
    assert body["max_level"] in VALID_LEVELS
    assert body["confidence"] in {"high", "medium", "low"}
    assert 0.0 <= body["overall_risk"] <= 1.0
    assert body["sol"] == GOLDEN_ROUTES[route_name]["sol"]

    for segment in body["segments"]:
        assert set(segment["factor_scores"]) == SPEC_FACTORS
        for assessment in segment["factor_scores"].values():
            assert assessment["available"] is True
            assert assessment["score"] is not None
            assert 0.0 <= assessment["score"] <= 1.0
        assert 0.0 <= segment["local_time_hour"] <= 23.0
        if segment["risk"] is not None:
            assert 0.0 <= segment["risk"] <= 1.0

    # MS5 reports radiation *rates* only — no route dose accumulation
    # anywhere in the response (that belongs to MS6).
    payload = json.dumps(body).lower()
    assert "dose" not in payload and "dosis" not in payload
