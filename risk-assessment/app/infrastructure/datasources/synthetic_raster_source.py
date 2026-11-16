"""Synthetic MS3 raster source: deterministic band values, no network.

Dev/test mode. Returns plausible values for the six canonical `rejilla`
bands inside the delivered grid extent; nodata -> None never occurs in
synthetic mode except where noted. Outside the extent reads raise
``NoCoverageError`` like MS3 does.
"""

import math
from collections.abc import Sequence

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import BandSample
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
)

# Same extent as synthetic_terrain_source (delivered rejilla grid).
_GALE_MIN_LON = 137.345
_GALE_MAX_LON = 137.455
_GALE_MIN_LAT = -4.740
_GALE_MAX_LAT = -4.580

# Canonical band order of rejilla_ruta_90m.tif (Phase 0 inventory).
BANDS: tuple[str, ...] = (
    "pendiente_grados",
    "rugosidad_m",
    "fraccion_oscura",
    "inercia_termica_tiu",
    "albedo",
    "distancia_duna_m",
)


class SyntheticRasterSource:
    def __init__(
        self,
        distance_calculator: DistanceCalculator,
        path_sampler: PathSampler,
        max_samples: int,
    ) -> None:
        self._path_sampler = path_sampler
        self._max_samples = max_samples

    def ping(self) -> bool:
        return True

    def dataset_bands(self) -> tuple[str, ...]:
        return BANDS

    def point_values(self, point: GeoPoint) -> dict[str, float | None]:
        self._check_coverage(point)
        return {band: self._value(band, point) for band in BANDS}

    def sample_band(
        self,
        band: str,
        path: Sequence[GeoPoint],
        sample_distance_m: float,
    ) -> tuple[BandSample, ...]:
        if band not in BANDS:
            raise DomainValidationError(f"Unknown band '{band}'; valid bands: {', '.join(BANDS)}")
        samples = self._path_sampler.sample(path, sample_distance_m, self._max_samples)
        for s in samples:
            self._check_coverage(s.point)
        return tuple(
            BandSample(
                lat=s.point.lat,
                lon=s.point.lon,
                distance_m=s.distance_m,
                value=self._value(band, s.point),
            )
            for s in samples
        )

    @staticmethod
    def _check_coverage(point: GeoPoint) -> None:
        if not (
            _GALE_MIN_LAT <= point.lat <= _GALE_MAX_LAT
            and _GALE_MIN_LON <= point.lon <= _GALE_MAX_LON
        ):
            raise NoCoverageError(f"Point ({point.lat}, {point.lon}) outside synthetic coverage")

    @staticmethod
    def _value(band: str, point: GeoPoint) -> float:
        fx = (point.lon - _GALE_MIN_LON) / (_GALE_MAX_LON - _GALE_MIN_LON)
        fy = (point.lat - _GALE_MIN_LAT) / (_GALE_MAX_LAT - _GALE_MIN_LAT)
        wave = math.sin(fx * 12.0) * math.cos(fy * 8.0)
        base = {
            "pendiente_grados": 4.0 + 10.0 * fx,
            "rugosidad_m": 0.3 + 1.2 * fy,
            "fraccion_oscura": 0.15 + 0.2 * fx,
            "inercia_termica_tiu": 420.0 + 15.0 * wave,
            "albedo": 0.228 + 0.004 * fx,
            "distancia_duna_m": 200.0 + 3000.0 * (1.0 - fx),
        }
        return round(base[band] + 0.05 * wave, 6)
