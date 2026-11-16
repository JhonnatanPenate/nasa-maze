"""Use case: risk evaluation along a polyline (SPEC §3.1/§4.1).

Calls MS4 `/terrain/profile` once per path and MS3 `/sample` once per
required band at the same arc-length step (SPEC §6 NFR). Segments are the
intervals between consecutive path samples (~``sampling_step_m`` apart).

Phase 1: factor scores are pending (Phase 3), so segment/overall risk is
``None`` and the level is ``unknown`` while ``available`` flags reflect
real data coverage.
"""

import math
from collections.abc import Sequence

from app.core.application.environment_context import (
    EnvironmentalContext,
    EnvironmentContextResolver,
)
from app.core.application.factor_builder import (
    DUNES_BANDS,
    ROUGHNESS_BAND,
    build_segment_assessments,
    provenance_for,
    raster_factors_requested,
    terrain_requested,
    validate_factor_selection,
)
from app.core.domain.factor_catalog import FACTOR_DUNES, FACTOR_ROUGHNESS
from app.core.domain.geo_point import GeoPoint
from app.core.domain.local_solar_time import validate_hour
from app.core.domain.observations import BandSample, SlopeSample
from app.core.domain.path_sample import PathSample
from app.core.domain.path_sampler import PathSampler
from app.core.domain.risk_aggregator import aggregate
from app.core.domain.risk_level import RiskLevel, level_for_score
from app.core.errors.exceptions import (
    DomainValidationError,
    UpstreamUnavailableError,
)
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.core.ports.vehicle_profile_repository import VehicleProfileRepository
from app.features.path_assessment.domain.path_risk import PathRisk, RiskSegment


class EvaluatePath:
    def __init__(
        self,
        terrain: TerrainSource,
        raster: RasterSource,
        env_resolver: EnvironmentContextResolver,
        vehicle_profiles: VehicleProfileRepository,
        path_sampler: PathSampler,
        weights: dict[str, float],
        default_vehicle_profile: str,
        max_path_points: int,
        max_samples: int,
        default_sampling_step_m: float,
    ) -> None:
        self._terrain = terrain
        self._raster = raster
        self._env_resolver = env_resolver
        self._vehicle_profiles = vehicle_profiles
        self._path_sampler = path_sampler
        self._weights = weights
        self._default_vehicle_profile = default_vehicle_profile
        self._max_path_points = max_path_points
        self._max_samples = max_samples
        self._default_sampling_step_m = default_sampling_step_m

    def execute(
        self,
        path: Sequence[GeoPoint],
        factors: Sequence[str] | None,
        sol: int | None,
        hora: int,
        sampling_step_m: float | None,
        vehicle_profile: str | None,
        speed_mps: float | None,
    ) -> PathRisk:
        selected = validate_factor_selection(factors)
        hour = self._validate_hora(hora)
        profile = self._vehicle_profiles.get(vehicle_profile or self._default_vehicle_profile)
        step = self._default_sampling_step_m if sampling_step_m is None else float(sampling_step_m)
        if not math.isfinite(step) or step <= 0.0:
            raise DomainValidationError(
                f"sampling_step_m must be a positive finite number, got {step}"
            )
        if len(path) > self._max_path_points:
            raise DomainValidationError(
                f"Path holds {len(path)} points, exceeding the limit of {self._max_path_points}"
            )

        positions = self._path_sampler.sample(path, step, self._max_samples)

        slope_samples = (
            self._terrain.slope_profile(path, step) if terrain_requested(selected) else ()
        )
        band_samples: dict[str, tuple[BandSample, ...]] = {}
        if raster_factors_requested(selected):
            for band in self._bands_for(selected):
                band_samples[band] = self._raster.sample_band(band, path, step)

        context = self._env_resolver.resolve(sol, hour)
        segments = self._build_segments(
            positions=positions,
            slope_samples=slope_samples,
            band_samples=band_samples,
            factors=selected,
            context=context,
        )
        overall, level = self._aggregate_overall(segments)

        provenance = provenance_for(context)
        provenance["vehicle_profile"] = profile.name
        provenance["sampling_step_m"] = step
        provenance["speed_mps_override"] = speed_mps

        return PathRisk(
            overall_risk=overall,
            level=level,
            segments=tuple(segments),
            warnings_summary=(),
            total_distance_m=positions[-1].distance_m,
            sol=context.reference_sol,
            hora=hour,
            vehicle_profile=profile.name,
            provenance=provenance,
            assumptions=(
                "Vehicle profile values are inherited optimizer assumptions, "
                "not certified flight limits.",
                "Factor scores pending Phase 3; available flags reflect data coverage only.",
            ),
        )

    # -- internals ------------------------------------------------------

    @staticmethod
    def _validate_hora(hora: int) -> int:
        try:
            return validate_hour(hora)
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

    @staticmethod
    def _bands_for(factors: Sequence[str]) -> tuple[str, ...]:
        bands: list[str] = []
        if FACTOR_ROUGHNESS in factors:
            bands.append(ROUGHNESS_BAND)
        if FACTOR_DUNES in factors:
            bands.extend(DUNES_BANDS)
        return tuple(dict.fromkeys(bands))

    def _build_segments(
        self,
        *,
        positions: Sequence[PathSample],
        slope_samples: tuple[SlopeSample, ...],
        band_samples: dict[str, tuple[BandSample, ...]],
        factors: Sequence[str],
        context: EnvironmentalContext,
    ) -> list[RiskSegment]:
        if terrain_requested(factors) and len(slope_samples) != len(positions):
            raise UpstreamUnavailableError(
                "Terrain service returned a sample count that does not match the path sampling"
            )
        for band, samples in band_samples.items():
            if len(samples) != len(positions):
                raise UpstreamUnavailableError(
                    f"Raster service returned {len(samples)} samples for band "
                    f"'{band}', expected {len(positions)}"
                )

        segments: list[RiskSegment] = []
        for i in range(len(positions) - 1):
            start = positions[i]
            end = positions[i + 1]
            # Assess the arrival sample of each interval.
            slope_sample = slope_samples[i + 1] if slope_samples else None
            band_map = {band: samples[i + 1] for band, samples in band_samples.items()}
            assessments = build_segment_assessments(
                factors=factors,
                slope_sample=slope_sample,
                band_samples=band_map,
                context=context,
            )
            risk, _level = aggregate(assessments, self._weights)
            segments.append(
                RiskSegment(
                    start=start.point,
                    end=end.point,
                    distance_m=end.distance_m - start.distance_m,
                    risk=risk,
                    factor_scores=assessments,
                )
            )
        return segments

    @staticmethod
    def _aggregate_overall(
        segments: Sequence[RiskSegment],
    ) -> tuple[float | None, RiskLevel]:
        """SPEC §4.1/plan §13.5: distance-weighted mean of segment risks;
        all-unscored -> (None, unknown)."""
        numerator = 0.0
        denominator = 0.0
        for segment in segments:
            if segment.risk is None or segment.distance_m <= 0.0:
                continue
            numerator += segment.risk * segment.distance_m
            denominator += segment.distance_m
        if denominator <= 0.0:
            return None, RiskLevel.UNKNOWN
        risk = numerator / denominator
        return min(1.0, max(0.0, risk)), level_for_score(risk)
