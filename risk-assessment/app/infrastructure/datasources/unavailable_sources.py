"""Unavailable upstreams: ping() False, every read -> UpstreamUnavailableError.

Used when ``RISK_DATASOURCE_MODE=unavailable`` or when an HTTP adapter
cannot be constructed (mirrors MS4's UnavailableRasterDatasource)."""

from collections.abc import Sequence

from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import BandSample, SlopeSample
from app.core.errors.exceptions import UpstreamUnavailableError


class UnavailableTerrainSource:
    def __init__(self, reason: str = "terrain source not configured") -> None:
        self._reason = reason

    def ping(self) -> bool:
        return False

    def slope_at(self, point: GeoPoint) -> float:
        raise UpstreamUnavailableError(f"Terrain source unavailable: {self._reason}")

    def slope_profile(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> tuple[SlopeSample, ...]:
        raise UpstreamUnavailableError(f"Terrain source unavailable: {self._reason}")


class UnavailableRasterSource:
    def __init__(self, reason: str = "raster source not configured") -> None:
        self._reason = reason

    def ping(self) -> bool:
        return False

    def dataset_bands(self) -> tuple[str, ...]:
        return ()

    def point_values(self, point: GeoPoint) -> dict[str, float | None]:
        raise UpstreamUnavailableError(f"Raster source unavailable: {self._reason}")

    def sample_band(
        self,
        band: str,
        path: Sequence[GeoPoint],
        sample_distance_m: float,
    ) -> tuple[BandSample, ...]:
        raise UpstreamUnavailableError(f"Raster source unavailable: {self._reason}")
