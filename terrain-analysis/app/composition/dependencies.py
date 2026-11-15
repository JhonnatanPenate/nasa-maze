from functools import lru_cache

import httpx
from fastapi import Depends

from app.core.application.terrain_point_sampler import TerrainPointSampler
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
from app.infrastructure.datasources.http_raster_datasource import (
    HttpRasterDatasource,
)
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)
from app.infrastructure.datasources.unavailable_raster_datasource import (
    UnavailableRasterDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from app.infrastructure.repositories.slope_grid_terrain_repository import (
    SlopeGridTerrainRepository,
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
    if settings.datasource_kind == "rejilla":
        if not settings.rejilla_path:
            raise ValueError(
                "Settings.rejilla_path (MS4_REJILLA_PATH) must point to a "
                "multi-band slope GeoTIFF when datasource_kind='rejilla'"
            )
        return GeoTiffRasterDatasource(
            settings.rejilla_path,
            mapper,
            settings.max_window_cells,
            band=settings.rejilla_slope_band,
        )
    if settings.datasource_kind == "http":
        client = httpx.Client(
            base_url=settings.raster_service_url,
            timeout=settings.raster_timeout_s,
        )
        return HttpRasterDatasource(
            client,
            mapper,
            dataset=settings.raster_dataset,
            band=settings.raster_band,
        )
    raise ValueError(
        f"Unsupported datasource_kind '{settings.datasource_kind}': expected "
        f"'synthetic', 'geotiff', 'rejilla' or 'http'"
    )


@lru_cache(maxsize=None)
def get_raster_datasource() -> RasterDatasource:
    """Process-wide datasource singleton.

    A build failure (e.g. invalid datasource_kind or missing dem_path)
    does not propagate: the fallback UnavailableRasterDatasource reports
    ping() False so /health degrades, and its reads surface as
    UpstreamDatasourceError -> 502.
    """
    try:
        return build_datasource(get_settings())
    except Exception as exc:
        return UnavailableRasterDatasource(exc)


def get_terrain_repository(
    datasource: RasterDatasource = Depends(get_raster_datasource),
    settings: Settings = Depends(get_settings),
) -> TerrainRepository:
    if settings.datasource_kind == "rejilla" or (
        settings.datasource_kind == "http"
        and settings.raster_values == "slope"
    ):
        return SlopeGridTerrainRepository(datasource)
    return DemTerrainRepository(datasource)


def get_slope_calculator() -> SlopeCalculator:
    return SlopeCalculator()


def get_terrain_classifier(
    settings: Settings = Depends(get_settings),
) -> TerrainClassifier:
    return TerrainClassifier(
        flat_max_deg=settings.slope_flat_max_deg,
        moderate_max_deg=settings.slope_moderate_max_deg,
        steep_max_deg=settings.slope_steep_max_deg,
    )


def get_distance_calculator(
    settings: Settings = Depends(get_settings),
) -> DistanceCalculator:
    return DistanceCalculator(settings.planet_radius_km * 1000.0)


def get_path_sampler(
    distance_calculator: DistanceCalculator = Depends(get_distance_calculator),
) -> PathSampler:
    return PathSampler(distance_calculator)


def get_terrain_point_sampler(
    repository: TerrainRepository = Depends(get_terrain_repository),
    slope_calculator: SlopeCalculator = Depends(get_slope_calculator),
) -> TerrainPointSampler:
    return TerrainPointSampler(repository, slope_calculator)
