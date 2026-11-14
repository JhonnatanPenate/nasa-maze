import pytest
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.features.area_analysis.presentation.area_router import router
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from tests.conftest import TEST_NODATA

HAPPY_BBOX = [77.49, 18.49, 77.51, 18.51]


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client(router)


@pytest.fixture
def failing_client(make_failing_client) -> TestClient:
    return make_failing_client(router)


class TestAreaEndpoint:
    def test_happy_path_exact_schema(self, client: TestClient) -> None:
        response = client.post(
            "/terrain/area",
            json={"body": "mars", "bbox": HAPPY_BBOX},
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"elevation_m", "slope_deg", "steep_fraction"}
        assert set(payload["elevation_m"]) == {"min", "max", "mean"}
        assert set(payload["slope_deg"]) == {"min", "max", "mean"}
        for stats in (payload["elevation_m"], payload["slope_deg"]):
            for value in stats.values():
                assert isinstance(value, float)
        assert isinstance(payload["steep_fraction"], float)
        # 3x3 window over cells rows/cols 9..11 of the plane DEM.
        assert payload["elevation_m"]["min"] == pytest.approx(485.0)
        assert payload["elevation_m"]["max"] == pytest.approx(495.0)
        assert payload["elevation_m"]["mean"] == pytest.approx(490.0)
        assert 0.0 <= payload["slope_deg"]["min"]
        assert payload["slope_deg"]["min"] <= payload["slope_deg"]["mean"]
        assert payload["slope_deg"]["mean"] <= payload["slope_deg"]["max"]
        assert payload["steep_fraction"] == pytest.approx(0.0)

    def test_body_field_is_optional(self, client: TestClient) -> None:
        response = client.post("/terrain/area", json={"bbox": HAPPY_BBOX})
        assert response.status_code == 200

    def test_inverted_bbox_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/terrain/area",
            json={"bbox": [77.51, 18.51, 77.49, 18.49]},
        )
        assert response.status_code == 400

    def test_short_bbox_is_422(self, client: TestClient) -> None:
        response = client.post(
            "/terrain/area", json={"bbox": [77.4, 18.4, 77.6]}
        )
        assert response.status_code == 422

    def test_missing_bbox_is_422(self, client: TestClient) -> None:
        response = client.post("/terrain/area", json={})
        assert response.status_code == 422

    def test_bbox_outside_extent_is_404(self, client: TestClient) -> None:
        response = client.post(
            "/terrain/area", json={"bbox": [80.0, 18.0, 81.0, 19.0]}
        )
        assert response.status_code == 404

    def test_nodata_only_bbox_is_404(self, client: TestClient) -> None:
        # Tiny bbox covering only the nodata cell (5, 5).
        response = client.post(
            "/terrain/area", json={"bbox": [77.452, 18.547, 77.453, 18.548]}
        )
        assert response.status_code == 404

    def test_max_window_cells_exceeded_is_400(
        self, make_client, small_dem, dem_window_mapper
    ) -> None:
        """A datasource built with a low cell cap rejects an oversized
        bbox with DomainValidationError -> 400."""
        elevation, extent = small_dem
        datasource = SyntheticDemDatasource(
            elevation,
            extent,
            dem_window_mapper,
            max_window_cells=4,
            nodata=TEST_NODATA,
        )
        client = make_client(
            router, datasource=datasource, settings=Settings(max_window_cells=4)
        )
        response = client.post(
            "/terrain/area", json={"bbox": [77.49, 18.49, 77.51, 18.51]}
        )
        assert response.status_code == 400

    def test_datasource_failure_is_502(
        self, failing_client: TestClient
    ) -> None:
        response = failing_client.post(
            "/terrain/area", json={"bbox": HAPPY_BBOX}
        )
        assert response.status_code == 502
