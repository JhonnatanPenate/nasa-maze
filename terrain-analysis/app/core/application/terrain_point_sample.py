from dataclasses import dataclass


@dataclass(frozen=True)
class TerrainPointSample:
    """Elevation and slope sampled at one coordinate."""

    elevation_m: float
    slope_deg: float
