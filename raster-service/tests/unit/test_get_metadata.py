import pytest

from app.core.domain.dataset_metadata import DatasetMetadata
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    UnknownDatasetError,
)
from app.features.datasets.application.get_metadata import GetMetadata
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource


class TestGetMetadata:
    def test_returns_domain_metadata(self, repository):
        metadata = GetMetadata(repository).execute("test")

        assert isinstance(metadata, DatasetMetadata)
        assert metadata.name == "test"
        assert metadata.width == 8
        assert metadata.height == 10
        assert metadata.band_names() == [
            "slope_deg",
            "roughness_m",
            "dark_fraction",
        ]

    def test_unknown_dataset_raises(self, repository):
        with pytest.raises(UnknownDatasetError):
            GetMetadata(repository).execute("nope")

    def test_unavailable_dataset_raises(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(DatasetUnavailableError):
            GetMetadata(repository).execute("broken")
