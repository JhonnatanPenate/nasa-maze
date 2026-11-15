from functools import lru_cache

from app.core.config.dataset_config import DatasetConfig
from app.core.config.settings import Settings
from app.core.ports.image_encoder import ImageEncoder
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.raster_repository import RasterRepository
from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.datasources.unavailable_raster_datasource import (
    UnavailableRasterDatasource,
)
from app.infrastructure.rendering.png_encoder import PngEncoder
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()


def build_datasource(name: str, config: DatasetConfig) -> RasterDatasource:
    """Select the RasterDatasource implementation for one dataset."""
    if config.kind == "geotiff":
        return GeoTiffRasterDatasource(config.path)
    if config.kind == "memory":
        return InMemoryRasterDatasource.synthetic()
    raise ValueError(
        f"Unsupported kind {config.kind!r} for dataset {name!r}: "
        f"expected 'geotiff' or 'memory'"
    )


def build_repository(settings: Settings) -> RasterRepository:
    """Build the dataset registry; a datasource that fails to build is
    replaced by UnavailableRasterDatasource so /health degrades and its
    reads surface as DatasetUnavailableError -> 503."""
    datasources: dict[str, RasterDatasource] = {}
    for name, config in settings.datasets.items():
        try:
            datasources[name] = build_datasource(name, config)
        except Exception as exc:
            datasources[name] = UnavailableRasterDatasource(exc)
    return RegistryRasterRepository(
        datasources=datasources,
        configs=settings.datasets,
        crs_label=settings.crs_label,
        planet_radius_km=settings.planet_radius_km,
    )


@lru_cache(maxsize=None)
def get_repository() -> RasterRepository:
    """Process-wide repository singleton (keeps the metadata cache)."""
    return build_repository(get_settings())


def get_image_encoder() -> ImageEncoder:
    return PngEncoder()
