from fastapi import Depends

from app.composition.dependencies import (
    get_path_sampler,
    get_raster_datasource,
    get_settings,
    get_slope_calculator,
)
from app.core.config.settings import Settings
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.ports.raster_datasource import RasterDatasource
from app.features.profile_analysis.application.analyze_profile import (
    AnalyzeProfile,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)


def get_analyze_profile(
    datasource: RasterDatasource = Depends(get_raster_datasource),
    path_sampler: PathSampler = Depends(get_path_sampler),
    slope_calculator: SlopeCalculator = Depends(get_slope_calculator),
    settings: Settings = Depends(get_settings),
) -> AnalyzeProfile:
    """Build AnalyzeProfile with the repository assembled here so that
    dependency_overrides on get_raster_datasource take effect."""
    repository = DemTerrainRepository(datasource)
    return AnalyzeProfile(
        repository=repository,
        path_sampler=path_sampler,
        slope_calculator=slope_calculator,
        max_path_points=settings.max_path_points,
        max_samples=settings.max_samples,
    )
