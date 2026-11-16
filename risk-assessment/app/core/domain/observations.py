"""Domain observations returned by the terrain/raster ports.

These are plain value objects shared by MS5 use cases; they mirror the
sample shapes MS3 (`/sample`, `/point`) and MS4 (`/profile`, `/point`)
return, so adapters translate 1:1.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SlopeSample:
    """Slope observation at one arc-length position along a path."""

    lat: float
    lon: float
    distance_m: float
    slope_deg: float | None


@dataclass(frozen=True)
class BandSample:
    """One raster band value at one arc-length position (None = nodata)."""

    lat: float
    lon: float
    distance_m: float
    value: float | None
