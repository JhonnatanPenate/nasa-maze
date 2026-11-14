from fastapi import Depends

from app.composition.dependencies import (
    get_raster_datasource,
    get_settings,
)
from app.core.config.settings import Settings
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.ports.raster_datasource import RasterDatasource
from app.features.area_analysis.application.analyze_area import AnalyzeArea
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)


def get_analyze_area(
    datasource: RasterDatasource = Depends(get_raster_datasource),
    settings: Settings = Depends(get_settings),
) -> AnalyzeArea:
    """AnalyzeArea provider.

    The repository is built here from Depends(get_raster_datasource) so
    test dependency_overrides on get_raster_datasource take effect.
    steep_min_deg is the lower bound of the `steep` terrain class
    (Settings.slope_moderate_max_deg, 15 deg by default).
    """
    return AnalyzeArea(
        repository=DemTerrainRepository(datasource),
        slope_calculator=SlopeCalculator(),
        steep_min_deg=settings.slope_moderate_max_deg,
    )
