"""Synthetic MS4 terrain source: deterministic slopes, no network.

Dev/test mode (``RISK_DATASOURCE_MODE=synthetic``). Values are a smooth
deterministic function of position inside the delivered Gale grid extent
so downstream code paths behave like real data; outside the extent it
raises ``NoCoverageError`` like MS4 does.
"""

import math
from collections.abc import Sequence

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.observations import SlopeSample
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import NoCoverageError

# Delivered rejilla grid bounds (Phase 0 inventory): inside the Gale AOI.
_GALE_MIN_LON = 137.345
_GALE_MAX_LON = 137.455
_GALE_MIN_LAT = -4.740
_GALE_MAX_LAT = -4.580


class SyntheticTerrainSource:
    def __init__(
        self,
        distance_calculator: DistanceCalculator,
        path_sampler: PathSampler,
        max_samples: int,
    ) -> None:
        self._distance_calculator = distance_calculator
        self._path_sampler = path_sampler
        self._max_samples = max_samples

    def ping(self) -> bool:
        return True

    def slope_at(self, point: GeoPoint) -> float:
        self._check_coverage(point)
        return self._slope(point)

    def slope_profile(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> tuple[SlopeSample, ...]:
        samples = self._path_sampler.sample(path, sample_distance_m, self._max_samples)
        for s in samples:
            self._check_coverage(s.point)
        return tuple(
            SlopeSample(
                lat=s.point.lat,
                lon=s.point.lon,
                distance_m=s.distance_m,
                slope_deg=self._slope(s.point),
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
    def _slope(point: GeoPoint) -> float:
        # Deterministic 0-30 deg ramp across the AOI; smooth, no network.
        fx = (point.lon - _GALE_MIN_LON) / (_GALE_MAX_LON - _GALE_MIN_LON)
        fy = (point.lat - _GALE_MIN_LAT) / (_GALE_MAX_LAT - _GALE_MIN_LAT)
        return round(2.0 + 18.0 * fx + 10.0 * fy + 3.0 * math.sin(fx * 9.0), 4)
