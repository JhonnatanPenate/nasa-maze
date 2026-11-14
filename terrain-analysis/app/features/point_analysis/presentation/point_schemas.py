from pydantic import BaseModel

from app.core.domain.terrain_class import TerrainClass


class PointAnalysisResponse(BaseModel):
    """Contract for `GET /terrain/point` (spec §4.1)."""

    lat: float
    lon: float
    elevation_m: float
    slope_deg: float
    terrain_class: TerrainClass
