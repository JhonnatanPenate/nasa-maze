from pydantic import BaseModel


class PathPointSchema(BaseModel):
    """One vertex of the request polyline; range checks happen in
    `GeoPoint` (400, not 422)."""

    lat: float
    lon: float


class SampleRequest(BaseModel):
    """Body of `POST /raster/{dataset}/sample` (spec §3.5). Path length
    and step limits are domain rules -> 400, not pydantic -> 422."""

    band: str
    path: list[PathPointSchema]
    sample_distance_m: float | None = None


class SampleEntryResponse(BaseModel):
    lat: float
    lon: float
    distance_m: float
    value: float | None


class SampleResponse(BaseModel):
    """Contract for `POST /raster/{dataset}/sample` (spec §4.5)."""

    band: str
    sample_count: int
    total_distance_m: float
    samples: list[SampleEntryResponse]
