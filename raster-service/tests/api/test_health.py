from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource


def _repository(datasources, configs):
    return RegistryRasterRepository(
        datasources=datasources,
        configs=configs,
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )


class TestHealth:
    def test_ok_when_all_datasets_readable(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "dataset_count": 1,
            "datasets": [{"name": "test", "readable": True}],
        }

    def test_degraded_when_a_dataset_is_unreadable(
        self, make_client, memory_datasource, api_dataset_config
    ):
        repository = _repository(
            {
                "test": memory_datasource,
                "broken": FailingRasterDatasource(),
            },
            {
                "test": api_dataset_config,
                "broken": api_dataset_config,
            },
        )
        client = make_client(repository=repository)

        response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["dataset_count"] == 2
        readable = {d["name"]: d["readable"] for d in body["datasets"]}
        assert readable == {"test": True, "broken": False}

    def test_zero_datasets_reports_ok(self, make_client):
        client = make_client(repository=_repository({}, {}))

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "dataset_count": 0,
            "datasets": [],
        }
