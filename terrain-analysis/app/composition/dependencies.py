from functools import lru_cache

from app.core.config.settings import Settings
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.ports.raster_datasource import RasterDatasource
from app.core.ports.terrain_repository import TerrainRepository
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)


@lru_cache(maxsize=None)
def get_settings() -> Settings:
    return Settings()


def build_datasource(settings: Settings) -> RasterDatasource:
    """Select the RasterDatasource implementation from settings."""
    mapper = DemWindowMapper(settings.planet_radius_km * 1000.0)
    if settings.datasource_kind == "synthetic":
        return SyntheticDemDatasource.default(mapper, settings.max_window_cells)
    if settings.datasource_kind == "geotiff":
        if not settings.dem_path:
            raise ValueError(
                "Settings.dem_path (MS4_DEM_PATH) must point to a GeoTIFF "
                "file when datasource_kind='geotiff'"
            )
        return GeoTiffRasterDatasource(
            settings.dem_path, mapper, settings.max_window_cells
        )
    raise ValueError(
        f"Unsupported datasource_kind '{settings.datasource_kind}': 'http' is "
        f"reserved for a future Raster Service (MS3) client"
    )


@lru_cache(maxsize=None)
def get_raster_datasource() -> RasterDatasource:
    return build_datasource(get_settings())


def get_terrain_repository() -> TerrainRepository:
    return DemTerrainRepository(get_raster_datasource())


def get_slope_calculator() -> SlopeCalculator:
    return SlopeCalculator()


def get_terrain_classifier() -> TerrainClassifier:
    settings = get_settings()
    return TerrainClassifier(
        flat_max_deg=settings.slope_flat_max_deg,
        moderate_max_deg=settings.slope_moderate_max_deg,
        steep_max_deg=settings.slope_steep_max_deg,
    )


def get_distance_calculator() -> DistanceCalculator:
    return DistanceCalculator(get_settings().planet_radius_km * 1000.0)


def get_path_sampler() -> PathSampler:
    return PathSampler(get_distance_calculator())
