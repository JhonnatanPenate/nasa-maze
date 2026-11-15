from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileSample:
    """One sampled point along a profile path, with terrain values."""

    lat: float
    lon: float
    distance_m: float
    elevation_m: float | None
    slope_deg: float
