"""In-memory failing sources for error-path tests (502 mapping)."""

from collections.abc import Sequence

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import BandSample, SlopeSample
from app.core.errors.exceptions import UpstreamUnavailableError


class FailingTerrainSource:
    def ping(self) -> bool:
        return False

    def slope_at(self, point: GeoPoint) -> float:
        raise UpstreamUnavailableError("terrain upstream down (test)")

    def slope_profile(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> tuple[SlopeSample, ...]:
        raise UpstreamUnavailableError("terrain upstream down (test)")


class FailingRasterSource:
    def ping(self) -> bool:
        return False

    def dataset_bands(self) -> tuple[str, ...]:
        return ()

    def point_values(self, point: GeoPoint) -> dict[str, float | None]:
        raise UpstreamUnavailableError("raster upstream down (test)")

    def sample_band(
        self,
        band: str,
        path: Sequence[GeoPoint],
        sample_distance_m: float,
    ) -> tuple[BandSample, ...]:
        raise UpstreamUnavailableError("raster upstream down (test)")
