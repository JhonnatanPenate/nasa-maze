import pytest

from app.features.point_analysis.presentation.point_router import router

# Small DEM: extent lon 77.4..77.6, lat 18.4..18.6, 21x21 cells,
# elevation[r, c] = 500 + 2c - 3r, nodata cell (5, 5).
CELL_DEG = 0.2 / 21.0
NODATA_LAT = 18.6 - 5.5 * CELL_DEG
NODATA_LON = 77.4 + 5.5 * CELL_DEG
EXPECTED_KEYS = {"lat", "lon", "elevation_m", "slope_deg", "terrain_class"}
TERRAIN_CLASSES = {"flat", "moderate", "steep", "hazardous"}


@pytest.fixture
def client(make_client):
    return make_client(router)


@pytest.fixture
def failing_client(make_failing_client):
    return make_failing_client(router)


class TestPointContract:
    def test_200_response_schema_and_values(self, client) -> None:
        response = client.get("/terrain/point", params={"lat": 18.5, "lon": 77.5})

        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == EXPECTED_KEYS
        assert isinstance(payload["lat"], float)
        assert isinstance(payload["lon"], float)
        assert isinstance(payload["elevation_m"], float)
        assert isinstance(payload["slope_deg"], float)
        assert payload["terrain_class"] in TERRAIN_CLASSES
        assert payload["lat"] == pytest.approx(18.5)
        assert payload["lon"] == pytest.approx(77.5)
        assert payload["elevation_m"] == pytest.approx(490.0)
        assert payload["slope_deg"] >= 0.0
        assert payload["terrain_class"] == "flat"

    def test_body_param_accepted_and_ignored(self, client) -> None:
        response = client.get(
            "/terrain/point",
            params={"lat": 18.5, "lon": 77.5, "body": "moon"},
        )
        assert response.status_code == 200
        assert set(response.json().keys()) == EXPECTED_KEYS


class TestPointValidation:
    @pytest.mark.parametrize(
        "params",
        [
            {"lat": 91.0, "lon": 77.5},
            {"lat": -91.0, "lon": 77.5},
            {"lat": 18.5, "lon": 181.0},
            {"lat": 18.5, "lon": -181.0},
        ],
    )
    def test_out_of_range_coordinate_returns_422(self, client, params) -> None:
        response = client.get("/terrain/point", params=params)
        assert response.status_code == 422

    @pytest.mark.parametrize("params", [{"lat": 18.5}, {"lon": 77.5}, {}])
    def test_missing_required_param_returns_422(self, client, params) -> None:
        response = client.get("/terrain/point", params=params)
        assert response.status_code == 422


class TestPointErrors:
    def test_nodata_cell_returns_404(self, client) -> None:
        response = client.get(
            "/terrain/point", params={"lat": NODATA_LAT, "lon": NODATA_LON}
        )
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_point_outside_extent_returns_404(self, client) -> None:
        response = client.get("/terrain/point", params={"lat": 17.0, "lon": 77.5})
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_datasource_failure_returns_502(self, failing_client) -> None:
        response = failing_client.get(
            "/terrain/point", params={"lat": 18.5, "lon": 77.5}
        )
        assert response.status_code == 502
        assert "detail" in response.json()
