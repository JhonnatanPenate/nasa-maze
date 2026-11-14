from pydantic import BaseModel


class PathPointSchema(BaseModel):
    """Polyline vertex. Ranges are intentionally unconstrained: GeoPoint
    and PathSampler raise DomainValidationError -> 400, not 422."""

    lat: float
    lon: float


class ProfileRequest(BaseModel):
    body: str = "mars"
    path: list[PathPointSchema]
    sample_distance_m: float | None = None


class ProfileSampleSchema(BaseModel):
    lat: float
    lon: float
    distance_m: float
    elevation_m: float
    slope_deg: float


class ProfileResponse(BaseModel):
    sample_count: int
    total_distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    max_slope_deg: float
    samples: list[ProfileSampleSchema]
