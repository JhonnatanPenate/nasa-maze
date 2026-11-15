from typing import Sequence

from app.core.application.terrain_point_sampler import TerrainPointSampler
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sampler import PathSampler
from app.core.errors.exceptions import DomainValidationError
from app.features.profile_analysis.domain.elevation_profile import (
    ElevationProfile,
)
from app.features.profile_analysis.domain.profile_sample import ProfileSample


class AnalyzeProfile:
    """Use case: sampled elevation/slope profile along a polyline (F3).

    PathSampler interpolates the path every sample_distance_m (enforcing
    <2 points, non-positive step and the max_samples cap as
    DomainValidationError). Each sample issues one TerrainPointSampler
    read; a NaN centre elevation raises NoCoverageError for the whole
    request, per the plan edge rule.
    """

    def __init__(
        self,
        sampler: TerrainPointSampler,
        path_sampler: PathSampler,
        max_path_points: int,
        max_samples: int,
    ) -> None:
        self._sampler = sampler
        self._path_sampler = path_sampler
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
            sample = self._sampler.sample(path_sample.point)
            samples.append(
                ProfileSample(
                    lat=path_sample.point.lat,
                    lon=path_sample.point.lon,
                    distance_m=path_sample.distance_m,
                    elevation_m=sample.elevation_m,
                    slope_deg=sample.slope_deg,
                )
            )

        if any(sample.elevation_m is None for sample in samples):
            gain_m = None
            loss_m = None
        else:
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
