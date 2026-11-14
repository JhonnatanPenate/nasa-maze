from fastapi import Depends

from app.composition.dependencies import (
    get_slope_calculator,
    get_terrain_classifier,
    get_terrain_repository,
)
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.domain.terrain_classifier import TerrainClassifier
from app.core.ports.terrain_repository import TerrainRepository
from app.features.area_analysis.application.analyze_area import AnalyzeArea


def get_analyze_area(
    repository: TerrainRepository = Depends(get_terrain_repository),
    slope_calculator: SlopeCalculator = Depends(get_slope_calculator),
    classifier: TerrainClassifier = Depends(get_terrain_classifier),
) -> AnalyzeArea:
    return AnalyzeArea(
        repository=repository,
        slope_calculator=slope_calculator,
        steep_min_deg=classifier.steep_min_deg,
    )
