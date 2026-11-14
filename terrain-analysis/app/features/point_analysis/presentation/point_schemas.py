from typing import Literal

from pydantic import BaseModel


class PointAnalysisResponse(BaseModel):
    """Contract for `GET /terrain/point` (spec §4.1)."""

    lat: float
    lon: float
    elevation_m: float
    slope_deg: float
    terrain_class: Literal["flat", "moderate", "steep", "hazardous"]
