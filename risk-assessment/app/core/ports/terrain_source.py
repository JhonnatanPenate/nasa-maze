"""Port: terrain observations (slope) — backed by MS4 Terrain Analysis."""

from collections.abc import Sequence
from typing import Protocol

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import SlopeSample


class TerrainSource(Protocol):
    """Slope provider. Implementations: HttpTerrainSource (MS4),
    SyntheticTerrainSource, UnavailableTerrainSource."""

    def ping(self) -> bool:
        """True when the source can serve terrain data."""
        ...

    def slope_at(self, point: GeoPoint) -> float:
        """Slope in degrees at one point. Raises NoCoverageError outside
        coverage and UpstreamUnavailableError when the source is down."""
        ...

    def slope_profile(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> tuple[SlopeSample, ...]:
        """Slope at every arc-length sample of ``path`` — one batched
        upstream call (SPEC §6 NFR). Sample positions follow the shared
        PathSampler convention (0, step, ..., end)."""
        ...
