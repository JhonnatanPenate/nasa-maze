from app.features.datasets.application.list_datasets import ListDatasets
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


class TestListDatasets:
    def test_lists_names_with_readability(self, repository):
        assert ListDatasets(repository).execute() == [("test", True)]

    def test_empty_registry_returns_empty_list(self):
        assert ListDatasets(_repository({}, {})).execute() == []

    def test_unreadable_dataset_is_flagged(self, dataset_config):
        repository = _repository(
            {"broken": FailingRasterDatasource()},
            {"broken": dataset_config},
        )

        assert ListDatasets(repository).execute() == [("broken", False)]
