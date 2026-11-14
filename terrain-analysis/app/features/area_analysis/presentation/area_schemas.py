from pydantic import BaseModel, Field


class AreaRequest(BaseModel):
    """Request body for POST /terrain/area.

    `body` is accepted for forward compatibility and ignored in the MVP.
    `bbox` is [min_lon, min_lat, max_lon, max_lat]; any other length is
    rejected with 422 before domain validation.
    """

    body: str = "mars"
    bbox: list[float] = Field(min_length=4, max_length=4)


class ValueStatsResponse(BaseModel):
    min: float
    max: float
    mean: float


class AreaResponse(BaseModel):
    elevation_m: ValueStatsResponse
    slope_deg: ValueStatsResponse
    steep_fraction: float
