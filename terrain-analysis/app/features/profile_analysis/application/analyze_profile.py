import math
from typing import Sequence

from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.domain.slope_calculator import SlopeCalculator
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
)
from app.core.ports.terrain_repository import TerrainRepository
from app.features.profile_analysis.domain.elevation_profile import (
    ElevationProfile,
)
from app.features.profile_analysis.domain.profile_sample import ProfileSample


class AnalyzeProfile:
    """Use case: sampled elevation/slope profile along a polyline (F3).

    PathSampler interpolates the path every sample_distance_m (enforcing
    <2 points, non-positive step and the max_samples cap as
    DomainValidationError). Each sample issues one repository.window_around
    read; a NaN centre elevation raises NoCoverageError for the whole
    request, per the plan edge rule.
    """

    def __init__(
        self,
        repository: TerrainRepository,
        path_sampler: PathSampler,
        slope_calculator: SlopeCalculator,
        max_path_points: int,
        max_samples: int,
    ) -> None:
        self._repository = repository
        self._path_sampler = path_sampler
        self._slope_calculator = slope_calculator
        self._max_path_points = max_path_points
        self._max_samples = max_samples

    def execute(
        self, path: Sequence[GeoPoint], sample_distance_m: float
    ) -> ElevationProfile:
        if len(path) > self._max_path_points:
            raise DomainValidationError(
                f"Path holds {len(path)} points, exceeding the limit "
                f"of {self._max_path_points}"
            )

        path_samples = self._path_sampler.sample(
            path, sample_distance_m, self._max_samples
        )

        samples: list[ProfileSample] = []
        for path_sample in path_samples:
            window = self._repository.window_around(path_sample.point, 1)
            elevation_m = window.center_value()
            if not math.isfinite(elevation_m):
                raise NoCoverageError(
                    f"No DEM coverage at lat={path_sample.point.lat}, "
                    f"lon={path_sample.point.lon}"
                )
            slope_deg = self._slope_calculator.compute_at_center(window)
            samples.append(
                ProfileSample(
                    lat=path_sample.point.lat,
                    lon=path_sample.point.lon,
                    distance_m=path_sample.distance_m,
                    elevation_m=elevation_m,
                    slope_deg=slope_deg,
                )
            )

        gain_m = 0.0
        loss_m = 0.0
        for previous, current in zip(samples, samples[1:]):
            delta = current.elevation_m - previous.elevation_m
            if delta > 0.0:
                gain_m += delta
            else:
                loss_m -= delta

        return ElevationProfile(
            samples=tuple(samples),
            total_distance_m=samples[-1].distance_m,
            elevation_gain_m=gain_m,
            elevation_loss_m=loss_m,
            max_slope_deg=max(sample.slope_deg for sample in samples),
        )
