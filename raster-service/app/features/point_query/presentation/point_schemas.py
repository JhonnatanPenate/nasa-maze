from pydantic import BaseModel


class PointResponse(BaseModel):
    """Contract for `GET /raster/{dataset}/point` (spec §4.3)."""

    lat: float
    lon: float
    values: dict[str, float | None]
