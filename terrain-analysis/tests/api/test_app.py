import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Full app against the DEFAULT datasource (no dependency overrides):
    the synthetic 1200x1200 DEM, lon 77-78 / lat 18-19."""
    return TestClient(app)


class TestCreateApp:
    def test_metadata(self) -> None:
        application = create_app()
        assert application.title == "MS4 Terrain Analysis Service"
        assert application.version == "0.1.0"

    def test_registers_all_routes(self) -> None:
        paths = set(create_app().openapi()["paths"].keys())
        assert {
            "/health",
            "/terrain/point",
            "/terrain/profile",
            "/terrain/area",
        } <= paths


class TestSmokeDefaultDatasource:
    """Plan §11 smoke requests against the synthetic DEM."""

    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "datasource": "ok",
            "datasource_kind": "synthetic",
        }

    def test_point(self, client: TestClient) -> None:
        response = client.get(
            "/terrain/point", params={"lat": 18.4, "lon": 77.5}
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {
            "lat",
            "lon",
            "elevation_m",
            "slope_deg",
            "terrain_class",
        }
        assert payload["lat"] == pytest.approx(18.4)
        assert payload["lon"] == pytest.approx(77.5)
        assert payload["terrain_class"] in {
            "flat",
            "moderate",
            "steep",
            "hazardous",
        }

    def test_profile(self, client: TestClient) -> None:
        response = client.post(
            "/terrain/profile",
            json={
                "path": [
                    {"lat": 18.4, "lon": 77.5},
                    {"lat": 18.5, "lon": 77.6},
                ],
                "sample_distance_m": 100,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {
            "sample_count",
            "total_distance_m",
            "elevation_gain_m",
            "elevation_loss_m",
            "max_slope_deg",
            "samples",
        }
        assert payload["sample_count"] == len(payload["samples"])
        assert payload["sample_count"] > 1
        for sample in payload["samples"]:
            assert set(sample.keys()) == {
                "lat",
                "lon",
                "distance_m",
                "elevation_m",
                "slope_deg",
            }

    def test_area(self, client: TestClient) -> None:
        # ~120x120 cells on the 1200x1200 default DEM — well under
        # max_window_cells.
        response = client.post(
            "/terrain/area", json={"bbox": [77.5, 18.4, 77.6, 18.5]}
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {
            "elevation_m",
            "slope_deg",
            "steep_fraction",
        }
        for stats in (payload["elevation_m"], payload["slope_deg"]):
            assert set(stats.keys()) == {"min", "max", "mean"}
            assert stats["min"] <= stats["mean"] <= stats["max"]
        assert 0.0 <= payload["steep_fraction"] <= 1.0
