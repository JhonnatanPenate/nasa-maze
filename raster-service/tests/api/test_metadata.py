import pytest

from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource


class TestMetadata:
    def test_metadata_schema_and_values(self, client):
        response = client.get("/raster/test/metadata")

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "test"
        assert body["crs"] == "IAU_2015:49900"
        assert body["bounds"] == [137.40, -4.70, 137.48, -4.60]
        assert body["width"] == 8
        assert body["height"] == 10
        assert body["resolution_deg"]["lon"] == pytest.approx(0.01)
        assert body["resolution_deg"]["lat"] == pytest.approx(0.01)
        # latitude cell size in metres: res_lat_deg * pi/180 * R (D: spec 4.2)
        assert body["resolution_m"] == pytest.approx(592.75, abs=0.1)
        assert body["bands"] == [
            {
                "index": 1,
                "name": "slope_deg",
                "unit": "deg",
                "nodata": -9999.0,
            },
            {
                "index": 2,
                "name": "roughness_m",
                "unit": "m",
                "nodata": -9999.0,
            },
            {
                "index": 3,
                "name": "dark_fraction",
                "unit": "fraction",
                "nodata": -9999.0,
            },
        ]

    def test_unknown_dataset_is_404_and_lists_valid_names(self, client):
        response = client.get("/raster/nope/metadata")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nope" in detail
        assert "test" in detail

    def test_unreadable_dataset_is_503(self, make_client, api_dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": api_dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = make_client(repository=repository)

        response = client.get("/raster/broken/metadata")

        assert response.status_code == 503
        assert "detail" in response.json()
