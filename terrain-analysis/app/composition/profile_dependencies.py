from fastapi import Depends

from app.composition.dependencies import (
    get_path_sampler,
    get_settings,
    get_terrain_point_sampler,
)
from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.config.settings import Settings
from app.core.domain.path_sampler import PathSampler
from app.features.profile_analysis.application.analyze_profile import (
    AnalyzeProfile,
)


def get_analyze_profile(
    sampler: TerrainPointSampler = Depends(get_terrain_point_sampler),
    path_sampler: PathSampler = Depends(get_path_sampler),
    settings: Settings = Depends(get_settings),
) -> AnalyzeProfile:
    return AnalyzeProfile(
        sampler=sampler,
        path_sampler=path_sampler,
        max_path_points=settings.max_path_points,
        max_samples=settings.max_samples,
    )
