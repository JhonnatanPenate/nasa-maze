from fastapi import Depends

from app.composition.dependencies import (
    get_raster_datasource,
    get_slope_calculator,
    get_terrain_classifier,
)
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.ports.raster_datasource import RasterDatasource
from app.features.point_analysis.application.analyze_point import AnalyzePoint
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)


def get_analyze_point(
    datasource: RasterDatasource = Depends(get_raster_datasource),
    slope_calculator: SlopeCalculator = Depends(get_slope_calculator),
    classifier: TerrainClassifier = Depends(get_terrain_classifier),
) -> AnalyzePoint:
    # The repository is built here rather than via get_terrain_repository
    # so that dependency_overrides on get_raster_datasource propagate.
    return AnalyzePoint(
        repository=DemTerrainRepository(datasource),
        slope_calculator=slope_calculator,
        classifier=classifier,
    )
