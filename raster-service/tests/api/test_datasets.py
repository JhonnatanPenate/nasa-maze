from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource


class TestListDatasets:
    def test_lists_registered_datasets_with_configured_path(self, client):
        response = client.get("/raster/datasets")

        assert response.status_code == 200
        assert response.json() == {
            "datasets": [
                {"name": "test", "path": "test/grid.tif", "readable": True}
            ]
        }

    def test_unreadable_dataset_flagged_but_listed(
        self, make_client, memory_datasource, api_dataset_config
    ):
        repository = RegistryRasterRepository(
            datasources={
                "test": memory_datasource,
                "broken": FailingRasterDatasource(),
            },
            configs={
                "test": api_dataset_config,
                "broken": api_dataset_config,
            },
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = make_client(repository=repository)

        response = client.get("/raster/datasets")

        assert response.status_code == 200
        entries = {
            d["name"]: d["readable"] for d in response.json()["datasets"]
        }
        assert entries == {"test": True, "broken": False}

    def test_empty_registry_returns_empty_list(self, make_client):
        repository = RegistryRasterRepository(
            datasources={},
            configs={},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = make_client(repository=repository)

        response = client.get("/raster/datasets")

        assert response.status_code == 200
        assert response.json() == {"datasets": []}
