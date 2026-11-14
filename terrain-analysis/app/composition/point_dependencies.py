from fastapi import Depends

from app.composition.dependencies import (
    get_terrain_classifier,
    get_terrain_point_sampler,
)
from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.domain.terrain_classifier import TerrainClassifier
from app.features.point_analysis.application.analyze_point import AnalyzePoint


def get_analyze_point(
    sampler: TerrainPointSampler = Depends(get_terrain_point_sampler),
    classifier: TerrainClassifier = Depends(get_terrain_classifier),
) -> AnalyzePoint:
    return AnalyzePoint(sampler=sampler, classifier=classifier)
