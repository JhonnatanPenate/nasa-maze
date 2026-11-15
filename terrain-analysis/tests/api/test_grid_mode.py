import pytest
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.features.area_analysis.presentation.area_router import (
    router as area_router,
)
from app.features.health.presentation.health_router import (
    router as health_router,
)
from app.features.point_analysis.presentation.point_router import (
    router as point_router,
)
from app.features.profile_analysis.presentation.profile_router import (
    router as profile_router,
)

# The default grid client (tests/api/conftest.py) serves a 5x5 slope
# grid over lon 100..105 / lat -10..-5; cell (2, 2), centred on
# lat=-7.5 / lon=102.5, is nodata.


class TestGridPoint:
    def test_200_with_null_elevation_and_slope(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(point_router)
        response = client.get(
            "/terrain/point", params={"lat": -8.5, "lon": 103.5}
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
        assert payload["elevation_m"] is None  # cell (3, 3) -> 19 deg
        assert payload["slope_deg"] == pytest.approx(19.0)
        assert payload["terrain_class"] == "steep"

    def test_nodata_cell_returns_404(self, make_grid_client) -> None:
        client = make_grid_client(point_router)
        response = client.get(
            "/terrain/point", params={"lat": -7.5, "lon": 102.5}
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_point_outside_extent_returns_404(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(point_router)
        response = client.get(
            "/terrain/point", params={"lat": 0.0, "lon": 103.5}
        )
        assert response.status_code == 404
        assert "detail" in response.json()


class TestGridProfile:
    def test_null_elevation_in_samples_and_aggregates(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(profile_router)
        response = client.post(
            "/terrain/profile",
            json={
                "path": [
                    {"lat": -9.5, "lon": 100.5},
                    {"lat": -5.5, "lon": 100.5},
                ],
                "sample_distance_m": 50000.0,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "elevation_gain_m" in body
        assert "elevation_loss_m" in body
        assert body["elevation_gain_m"] is None
        assert body["elevation_loss_m"] is None
        assert body["sample_count"] == len(body["samples"]) > 1
        for sample in body["samples"]:
            assert "elevation_m" in sample
            assert sample["elevation_m"] is None
            assert isinstance(sample["slope_deg"], float)
        assert body["max_slope_deg"] == pytest.approx(21.0)

    def test_path_through_nodata_returns_404(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(profile_router)
        response = client.post(
            "/terrain/profile",
            json={
                "path": [
                    {"lat": -7.5, "lon": 102.4},
                    {"lat": -7.5, "lon": 102.6},
                ],
                "sample_distance_m": 1000.0,
            },
        )
        assert response.status_code == 404


class TestGridArea:
    def test_null_elevation_and_slope_stats(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(area_router)
        response = client.post(
            "/terrain/area",
            json={"bbox": [100.0, -10.0, 105.0, -5.0]},
        )

        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {
            "elevation_m",
            "slope_deg",
            "steep_fraction",
        }
        assert payload["elevation_m"] is None
        # 24 valid cells (13 deg at (2, 2) is nodata): 11 of them are
        # >= the 15 deg steep threshold.
        assert payload["slope_deg"]["min"] == pytest.approx(1.0)
        assert payload["slope_deg"]["max"] == pytest.approx(25.0)
        assert payload["slope_deg"]["mean"] == pytest.approx(13.0)
        assert payload["steep_fraction"] == pytest.approx(11.0 / 24.0)

    def test_bbox_outside_extent_returns_404(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(area_router)
        response = client.post(
            "/terrain/area",
            json={"bbox": [110.0, -10.0, 111.0, -5.0]},
        )
        assert response.status_code == 404


class TestGridHealth:
    def test_reports_default_datasource_kind(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(health_router)
        response = client.get("/health")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["datasource"] == "ok"
        assert payload["datasource_kind"] == "synthetic"

    def test_echoes_configured_datasource_kind(
        self, make_grid_client
    ) -> None:
        client = make_grid_client(
            health_router,
            settings=Settings(datasource_kind="rejilla"),
        )
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["datasource_kind"] == "rejilla"
