from dataclasses import dataclass

from app.core.domain.terrain_class import TerrainClass


@dataclass(frozen=True)
class PointAnalysis:
    """Result of a single-point terrain analysis."""

    lat: float
    lon: float
    elevation_m: float
    slope_deg: float
    terrain_class: TerrainClass
