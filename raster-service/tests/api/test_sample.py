import pytest

from app.core.config.settings import Settings
from app.features.path_sampling.presentation.sample_router import router
from tests.conftest import TEST_DATASET, mount_router

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8 cols
# of 0.01 deg. Band "slope_deg" holds row*10 + col (nodata at (1,1)).
# A meridian path down column 0 from lat -4.605 to -4.695 crosses rows
# 0..9 -> values 0,10,...,90 at the default step (one cell ~592.75 m).


@pytest.fixture
def client(api_repository, api_settings):
    return mount_router(router, api_repository, api_settings)


class TestSample:
    def test_meridian_path_default_step(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.695, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {
            "band",
            "sample_count",
            "total_distance_m",
            "samples",
        }
        assert body["band"] == "slope_deg"
        assert body["sample_count"] == 10
        assert body["total_distance_m"] == pytest.approx(
            5334.722, rel=1e-3
        )
        assert len(body["samples"]) == 10
        first = body["samples"][0]
        assert first == {
            "lat": pytest.approx(-4.605),
            "lon": pytest.approx(137.405),
            "distance_m": 0.0,
            "value": 0.0,
        }
        last = body["samples"][-1]
        assert last["lat"] == pytest.approx(-4.695)
        assert last["distance_m"] == pytest.approx(body["total_distance_m"])
        assert last["value"] == 90.0
        assert [s["value"] for s in body["samples"]] == [
            float(10 * r) for r in range(10)
        ]

    def test_explicit_step_skips_rows(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.695, "lon": 137.405},
                ],
                "sample_distance_m": 3000.0,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert [s["value"] for s in body["samples"]] == [0.0, 50.0, 90.0]
        assert body["sample_count"] == 3

    def test_nodata_cell_reports_null(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.615, "lon": 137.415},
                    {"lat": -4.615, "lon": 137.425},
                ],
                "sample_distance_m": 10_000.0,
            },
        )

        assert response.status_code == 200
        values = [s["value"] for s in response.json()["samples"]]
        assert values == [None, 12.0]

    def test_partially_outside_path_reports_nulls(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.595, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 200
        values = [s["value"] for s in response.json()["samples"]]
        assert values == [0.0, None]

    def test_fully_outside_path_is_404(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.55, "lon": 137.405},
                    {"lat": -4.56, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 404

    def test_single_point_path_is_400(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [{"lat": -4.605, "lon": 137.405}],
            },
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_empty_path_is_400(self, client):
        response = client.post(
            "/raster/test/sample",
            json={"band": "slope_deg", "path": []},
        )

        assert response.status_code == 400

    @pytest.mark.parametrize("bad_step", [0.0, -5.0])
    def test_non_positive_step_is_400(self, client, bad_step):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.615, "lon": 137.405},
                ],
                "sample_distance_m": bad_step,
            },
        )

        assert response.status_code == 400

    def test_more_than_max_path_points_is_400(
        self, api_repository, api_dataset_config
    ):
        settings = Settings(
            datasets={TEST_DATASET: api_dataset_config}, max_path_points=3
        )
        client = mount_router(router, api_repository, settings)
        path = [
            {"lat": -4.605 - 0.001 * k, "lon": 137.405} for k in range(4)
        ]

        response = client.post(
            "/raster/test/sample",
            json={"band": "slope_deg", "path": path},
        )

        assert response.status_code == 400

    def test_more_than_max_samples_is_400(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.695, "lon": 137.405},
                ],
                "sample_distance_m": 1.0,  # ~5335 samples > max_samples 1000
            },
        )

        assert response.status_code == 400

    def test_out_of_range_latitude_is_400(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": 95.0, "lon": 137.405},
                    {"lat": -4.605, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 400

    def test_unknown_band_is_404_and_lists_valid_names(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "nope",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.615, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nope" in detail
        assert "slope_deg" in detail

    def test_unknown_dataset_is_404(self, client):
        response = client.post(
            "/raster/nope/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": -4.605, "lon": 137.405},
                    {"lat": -4.615, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 404

    def test_malformed_body_is_422(self, client):
        response = client.post(
            "/raster/test/sample",
            json={"path": [{"lat": -4.605, "lon": 137.405}]},
        )

        assert response.status_code == 422

    def test_non_numeric_coordinate_is_422(self, client):
        response = client.post(
            "/raster/test/sample",
            json={
                "band": "slope_deg",
                "path": [
                    {"lat": "abc", "lon": 137.405},
                    {"lat": -4.615, "lon": 137.405},
                ],
            },
        )

        assert response.status_code == 422
