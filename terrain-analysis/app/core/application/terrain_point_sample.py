from dataclasses import dataclass


@dataclass(frozen=True)
class TerrainPointSample:
    """Elevation and slope sampled at one coordinate."""

    elevation_m: float | None
    slope_deg: float
