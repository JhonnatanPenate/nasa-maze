import pytest

from app.composition.dependencies import (
    build_datasource,
    build_repository,
    get_image_encoder,
    get_repository,
    get_settings,
)
from app.core.config.dataset_config import DatasetConfig
from app.core.config.settings import Settings
from app.core.errors.exceptions import DatasetUnavailableError
from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.rendering.png_encoder import PngEncoder
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)


class TestGetSettings:
    def test_returns_settings_with_default_registry(self):
        settings = get_settings()

        assert isinstance(settings, Settings)
        assert "rejilla" in settings.datasets
        assert settings.datasets["rejilla"].kind == "geotiff"

    def test_is_cached(self):
        assert get_settings() is get_settings()


class TestBuildDatasource:
    def test_geotiff_kind_builds_geotiff_datasource(self, geotiff_path):
        config = DatasetConfig(path=str(geotiff_path), kind="geotiff")

        datasource = build_datasource("test", config)

        assert isinstance(datasource, GeoTiffRasterDatasource)
        assert datasource.ping() is True

    def test_memory_kind_builds_in_memory_datasource(self):
        config = DatasetConfig(path="", kind="memory")

        datasource = build_datasource("test", config)

        assert isinstance(datasource, InMemoryRasterDatasource)
        assert datasource.ping() is True


class TestBuildRepository:
    def test_build_failure_falls_back_to_unavailable(self):
        bad = DatasetConfig.model_construct(path="x", kind="bogus")
        settings = Settings(datasets={"bad": bad})

        repository = build_repository(settings)

        assert repository.dataset_names() == ["bad"]
        assert repository.is_readable("bad") is False
        with pytest.raises(DatasetUnavailableError):
            repository.metadata("bad")

    def test_empty_registry_builds_empty_repository(self):
        repository = build_repository(Settings(datasets={}))

        assert repository.dataset_names() == []

    def test_memory_registry_is_readable(self):
        settings = Settings(
            datasets={"demo": DatasetConfig(path="", kind="memory")}
        )

        repository = build_repository(settings)

        assert repository.is_readable("demo") is True
        assert repository.metadata("demo").band_names() == [
            "pendiente_grados",
            "rugosidad_m",
            "fraccion_oscura",
            "inercia_termica_tiu",
            "albedo",
            "distancia_duna_m",
        ]


class TestProviders:
    def test_get_repository_returns_registry(self):
        assert isinstance(get_repository(), RegistryRasterRepository)

    def test_get_repository_is_cached(self):
        assert get_repository() is get_repository()

    def test_get_image_encoder_returns_png_encoder(self):
        encoder = get_image_encoder()

        assert isinstance(encoder, PngEncoder)
