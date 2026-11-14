import time

import pytest

from app.features.profile_analysis.presentation.profile_router import router


@pytest.fixture
def client(make_client):
    return make_client(router)


@pytest.fixture
def failing_client(make_failing_client):
    return make_failing_client(router)


def test_profile_returns_contract_response(client):
    response = client.post(
        "/terrain/profile",
        json={
            "body": "mars",
            "path": [
                {"lat": 18.55, "lon": 77.5},
                {"lat": 18.45, "lon": 77.5},
            ],
            "sample_distance_m": 2000.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "sample_count",
        "total_distance_m",
        "elevation_gain_m",
        "elevation_loss_m",
        "max_slope_deg",
        "samples",
    }
    assert body["sample_count"] == 4
    assert len(body["samples"]) == body["sample_count"]
    for sample in body["samples"]:
        assert set(sample.keys()) == {
            "lat",
            "lon",
            "distance_m",
            "elevation_m",
            "slope_deg",
        }
    assert body["samples"][0]["distance_m"] == pytest.approx(0.0)
    assert body["samples"][0]["lat"] == pytest.approx(18.55)
    assert body["samples"][0]["lon"] == pytest.approx(77.5)
    assert body["total_distance_m"] == pytest.approx(
        body["samples"][-1]["distance_m"]
    )
    # Due-south path descends: all loss, no gain.
    assert body["elevation_gain_m"] == pytest.approx(0.0)
    assert body["elevation_loss_m"] == pytest.approx(30.0)
    assert body["max_slope_deg"] > 0.0


def test_default_sample_distance_used_when_omitted(client):
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.5, "lon": 77.5},
                {"lat": 18.49, "lon": 77.5},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    # 0.01 deg of latitude is ~591 m on Mars -> 5 full 100 m steps + tail.
    assert body["sample_count"] == 7
    assert body["samples"][1]["distance_m"] == pytest.approx(100.0)


def test_one_point_path_returns_400(client):
    response = client.post(
        "/terrain/profile",
        json={"path": [{"lat": 18.5, "lon": 77.5}]},
    )
    assert response.status_code == 400


def test_zero_sample_distance_returns_400(client):
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.5, "lon": 77.5},
                {"lat": 18.49, "lon": 77.5},
            ],
            "sample_distance_m": 0.0,
        },
    )
    assert response.status_code == 400


def test_out_of_range_latitude_returns_400(client):
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 95.0, "lon": 77.5},
                {"lat": 18.49, "lon": 77.5},
            ]
        },
    )
    assert response.status_code == 400


def test_too_many_path_points_returns_400(client):
    response = client.post(
        "/terrain/profile",
        json={"path": [{"lat": 18.5, "lon": 77.5}] * 101},
    )
    assert response.status_code == 400


def test_missing_path_returns_422(client):
    response = client.post("/terrain/profile", json={})
    assert response.status_code == 422


def test_non_numeric_latitude_returns_422(client):
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": "abc", "lon": 77.5},
                {"lat": 18.49, "lon": 77.5},
            ]
        },
    )
    assert response.status_code == 422


def test_path_through_nodata_returns_404(client):
    """Cell (5, 5) of the test DEM is nodata; a path sample landing there
    must 404 the whole request."""
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.55, "lon": 77.45},
                {"lat": 18.55, "lon": 77.46},
            ]
        },
    )
    assert response.status_code == 404


def test_path_outside_extent_returns_404(client):
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.7, "lon": 77.5},
                {"lat": 18.71, "lon": 77.5},
            ]
        },
    )
    assert response.status_code == 404


def test_failing_datasource_returns_502(failing_client):
    response = failing_client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.55, "lon": 77.5},
                {"lat": 18.45, "lon": 77.5},
            ]
        },
    )
    assert response.status_code == 502


def test_hundred_sample_profile_completes_under_two_seconds(client):
    started = time.perf_counter()
    response = client.post(
        "/terrain/profile",
        json={
            "path": [
                {"lat": 18.6, "lon": 77.5},
                {"lat": 18.4, "lon": 77.5},
            ],
            "sample_distance_m": 110.0,
        },
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert response.json()["sample_count"] >= 100
    assert elapsed < 2.0
