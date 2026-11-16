"""Use case: risk evaluation along a polyline (SPEC §3.1/§4.1).

Calls MS4 ``POST /terrain/profile`` once per path and MS3
``POST /raster/{dataset}/sample`` once per required band at the same
arc-length step (SPEC §6 NFR). Segments are the intervals between
consecutive path samples (~``sampling_step_m`` apart).

Path evaluation always fetches terrain + the soil/tilt raster bands:
they feed the SPEC raster factors AND the additive vehicle-profile
restrictions (soil classification -> tilt prediction -> effective speed
-> per-segment LMST advance, plan §4.4/§7.1). ``factors`` only selects
which factors are scored and aggregated.

``hora`` is the departure LMST bin; each segment's arrival hour advances
by ``distance / effective_speed`` hours with mod-24 wrap (Javi's 24-bin
convention). The nearest environmental sol per dataset is resolved once
and stays fixed along the path. Radiation stays a per-segment *rate* —
route dose accumulation belongs to MS6.
"""

import math
from collections.abc import Sequence

from app.core.application.environment_context import EnvironmentContextResolver
from app.core.application.factor_builder import (
    PATH_BANDS,
    ROUGHNESS_BAND,
    ScoringThresholds,
    build_segment_assessments,
    coverage_confidence,
    coverage_notes,
    level_rank,
    merged_warnings,
    provenance_for,
    scored_cell_counts,
    sol_fallback_notes,
    validate_factor_selection,
)
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import SPEC_FACTORS
from app.core.domain.geo_point import GeoPoint
from app.core.domain.local_solar_time import validate_hour
from app.core.domain.observations import BandSample, SlopeSample
from app.core.domain.path_sample import PathSample
from app.core.domain.path_sampler import PathSampler
from app.core.domain.restriction import evaluate_restrictions
from app.core.domain.risk_aggregator import aggregate, aggregate_path
from app.core.domain.risk_level import RiskLevel
from app.core.domain.soil_type import classify_soil
from app.core.domain.temperature_risk import thermal_excess_K
from app.core.domain.tilt_model import TiltModelSet, predict_tilt
from app.core.domain.vehicle_profile import (
    VehicleProfile,
    effective_speed_m_h,
    travel_hours,
)
from app.core.errors.exceptions import (
    DomainValidationError,
    UpstreamUnavailableError,
)
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.core.ports.vehicle_profile_repository import VehicleProfileRepository
from app.features.path_assessment.domain.path_risk import PathRisk, RiskSegment

_HOT_LEVELS = (RiskLevel.HIGH, RiskLevel.CRITICAL)


class EvaluatePath:
    def __init__(
        self,
        terrain: TerrainSource,
        raster: RasterSource,
        env_resolver: EnvironmentContextResolver,
        vehicle_profiles: VehicleProfileRepository,
        path_sampler: PathSampler,
        weights: dict[str, float],
        thresholds: ScoringThresholds,
        tilt_models: TiltModelSet,
        model_version: str,
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
        self._thresholds = thresholds
        self._tilt_models = tilt_models
        self._model_version = model_version
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
        speed_override_m_h = self._validate_speed(speed_mps)
        if len(path) > self._max_path_points:
            raise DomainValidationError(
                f"Path holds {len(path)} points, exceeding the limit of {self._max_path_points}"
            )

        positions = self._path_sampler.sample(path, step, self._max_samples)

        # One batched MS4 call + one MS3 call per soil band (SPEC §6 NFR).
        slope_samples = self._terrain.slope_profile(path, step)
        band_samples = {
            band: self._raster.sample_band(band, path, step) for band in PATH_BANDS
        }

        reference = self._env_resolver.resolve(sol, hour)
        daily_predictors = self._env_resolver.daily_predictors(reference)

        built = self._build_segments(
            positions=positions,
            slope_samples=slope_samples,
            band_samples=band_samples,
            factors=selected,
            sol=sol,
            departure_hour=hour,
            profile=profile,
            speed_override_m_h=speed_override_m_h,
            daily_predictors=daily_predictors,
        )
        overall, level = aggregate_path(
            [(s.risk, s.distance_m) for s in built.segments]
        )

        provenance = provenance_for(reference, self._model_version)
        provenance["vehicle_profile"] = profile.name
        provenance["sampling_step_m"] = step
        provenance["speed_mps_override"] = speed_mps
        provenance["thermal_excess_Kh"] = round(built.thermal_excess_kh, 6)

        scored, total = scored_cell_counts(
            [s.factor_scores for s in built.segments]
        )
        notes = (
            sol_fallback_notes([reference])
            + coverage_notes(selected, [s.factor_scores for s in built.segments])
            + built.extra_notes
        )

        return PathRisk(
            overall_risk=overall,
            level=level,
            segments=tuple(built.segments),
            warnings_summary=merged_warnings(
                [s.factor_scores for s in built.segments]
            ),
            total_distance_m=positions[-1].distance_m,
            sol=reference.reference_sol,
            hora=hour,
            vehicle_profile=profile.name,
            max_level=built.max_level,
            mean_score=built.mean_score,
            p95_score=built.p95_score,
            dominant_factor=built.dominant_factor,
            total_duration_s=built.total_hours * 3600.0,
            end_local_time_hours=(hour + built.total_hours) % 24,
            confidence=coverage_confidence(scored, total),
            provenance=provenance,
            data_quality_notes=notes,
            assumptions=(
                "Vehicle profile values are inherited optimizer assumptions, "
                "not certified flight limits.",
                "Per-segment LMST advances by effective-speed travel time "
                "(24-bin wrap); selected environmental sols stay fixed.",
                "Predicted tilt uses per-soil linear models with global "
                "fallback; placeholder thresholds are in docs/DECISIONS.md.",
            ),
            restrictions=tuple(built.restrictions),
            hotspots=tuple(built.hotspots),
            blocking_segments=tuple(built.blocking_segments),
        )

    # -- internals ------------------------------------------------------

    @staticmethod
    def _validate_hora(hora: int) -> int:
        try:
            return validate_hour(hora)
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

    @staticmethod
    def _validate_speed(speed_mps: float | None) -> float | None:
        if speed_mps is None:
            return None
        speed = float(speed_mps)
        if not math.isfinite(speed) or speed <= 0.0:
            raise DomainValidationError(
                f"speed_mps must be a positive finite number, got {speed_mps}"
            )
        return speed * 3600.0  # m/s -> m/h for the Javi profile formulas

    def _build_segments(
        self,
        *,
        positions: Sequence[PathSample],
        slope_samples: tuple[SlopeSample, ...],
        band_samples: dict[str, tuple[BandSample, ...]],
        factors: Sequence[str],
        sol: int | None,
        departure_hour: int,
        profile: VehicleProfile,
        speed_override_m_h: float | None,
        daily_predictors: dict[str, float],
    ) -> "_SegmentBuild":
        if len(slope_samples) != len(positions):
            raise UpstreamUnavailableError(
                "Terrain service returned a sample count that does not match the path sampling"
            )
        for band, samples in band_samples.items():
            if len(samples) != len(positions):
                raise UpstreamUnavailableError(
                    f"Raster service returned {len(samples)} samples for band "
                    f"'{band}', expected {len(positions)}"
                )

        build = _SegmentBuild()

        for i in range(len(positions) - 1):
            start = positions[i]
            end = positions[i + 1]
            segment_m = end.distance_m - start.distance_m

            slope_sample = slope_samples[i + 1]
            slope_deg = slope_sample.slope_deg
            band_map = {band: samples[i + 1] for band, samples in band_samples.items()}
            band_values = {
                band: (sample.value if sample else None)
                for band, sample in band_map.items()
            }

            soil = classify_soil(
                rugosidad_m=band_values.get(ROUGHNESS_BAND),
                pendiente_grados=slope_deg,
                albedo=band_values.get("albedo"),
                distancia_duna_m=band_values.get("distancia_duna_m"),
                fraccion_oscura=band_values.get("fraccion_oscura"),
            )
            tilt = predict_tilt(
                self._tilt_models,
                soil=soil,
                raster_predictors={
                    "pendiente_grados": slope_deg,
                    "rugosidad": band_values.get(ROUGHNESS_BAND),
                    "inercia_termica_tiu": band_values.get("inercia_termica_tiu"),
                    "albedo": band_values.get("albedo"),
                },
                daily_predictors=daily_predictors,
            )
            if tilt is not None and tilt.model_label.startswith("global"):
                build.tilt_global_count += 1

            speed_m_h = (
                speed_override_m_h
                if speed_override_m_h is not None
                else effective_speed_m_h(
                    profile,
                    tilt_deg=tilt.tilt_deg if tilt is not None else None,
                    soil=soil,
                )
            )
            segment_hours = travel_hours(segment_m, speed_m_h)
            build.total_hours += segment_hours
            # Arrival LMST bin: Javi's int(t) % 24 on departure + elapsed.
            segment_hour = int(departure_hour + build.total_hours) % 24

            context = self._env_resolver.resolve(sol, segment_hour)
            assessments = build_segment_assessments(
                factors=factors,
                slope_sample=slope_sample,
                band_samples=band_map,
                context=context,
                thresholds=self._thresholds,
            )
            risk, level = aggregate(assessments, self._weights)
            build.levels.append(level)

            temp_mean_K = (
                context.temperature.ground_temp_mean_K if context.temperature else None
            )
            if temp_mean_K is not None:
                build.thermal_excess_kh += (
                    thermal_excess_K(
                        temp_mean_K,
                        self._thresholds.temperature.band_min_K,
                        self._thresholds.temperature.band_max_K,
                    )
                    * segment_hours
                )
            if (
                context.radiation is not None
                and context.radiation.provenance == "sol_mean_fallback"
            ):
                build.radiation_fallback_count += 1

            segment_restrictions = evaluate_restrictions(
                profile,
                slope_deg=slope_deg,
                tilt=tilt,
                temp_mean_K=temp_mean_K,
            )
            for restriction in segment_restrictions:
                build.restrictions.append(
                    {
                        "segment": i,
                        "code": restriction.code,
                        "blocking": restriction.blocking,
                        "message": restriction.message,
                        "factor": restriction.factor,
                        "value": restriction.value,
                        "limit": restriction.limit,
                    }
                )
            if any(r.blocking for r in segment_restrictions):
                build.blocking_segments.append(i)
            if level in _HOT_LEVELS:
                build.hotspots.append(
                    {
                        "segment": i,
                        "risk": risk,
                        "level": level.value,
                        "distance_m": segment_m,
                    }
                )

            build.segments.append(
                RiskSegment(
                    start=start.point,
                    end=end.point,
                    distance_m=segment_m,
                    risk=risk,
                    factor_scores=assessments,
                    warnings=_factor_warnings(assessments),
                    local_time_hour=segment_hour,
                )
            )
            build.assessments_per_segment.append(assessments)

        build._summarize()
        return build


class _SegmentBuild:
    """Mutable accumulator for one path evaluation (internal)."""

    def __init__(self) -> None:
        self.segments: list[RiskSegment] = []
        self.assessments_per_segment: list[tuple[FactorAssessment, ...]] = []
        self.levels: list[RiskLevel] = []
        self.restrictions: list[dict[str, object]] = []
        self.blocking_segments: list[int] = []
        self.hotspots: list[dict[str, object]] = []
        self.total_hours = 0.0
        self.thermal_excess_kh = 0.0
        self.tilt_global_count = 0
        self.radiation_fallback_count = 0
        self.max_level: RiskLevel | None = None
        self.mean_score: float | None = None
        self.p95_score: float | None = None
        self.dominant_factor: str | None = None
        self.extra_notes: tuple[str, ...] = ()

    def _summarize(self) -> None:
        scored_risks = sorted(s.risk for s in self.segments if s.risk is not None)
        self.max_level = (
            max(self.levels, key=level_rank) if self.levels else RiskLevel.UNKNOWN
        )
        if scored_risks:
            self.mean_score = sum(scored_risks) / len(scored_risks)
            # Nearest-rank p95 over segment risks (plan "summary mean/p95").
            self.p95_score = scored_risks[max(0, math.ceil(0.95 * len(scored_risks)) - 1)]
        self.dominant_factor = _dominant_factor(self.assessments_per_segment)

        notes: list[str] = []
        total_segments = len(self.segments)
        if self.tilt_global_count:
            notes.append(
                f"tilt predicted with the global model on "
                f"{self.tilt_global_count}/{total_segments} segments"
            )
        if self.radiation_fallback_count:
            notes.append(
                f"RAD sol-mean hourly fallback used on "
                f"{self.radiation_fallback_count}/{total_segments} segments"
            )
        self.extra_notes = tuple(notes)


def _factor_warnings(
    assessments: Sequence[FactorAssessment],
) -> tuple[str, ...]:
    """Union of one segment's factor warnings, first-seen order."""
    return tuple(dict.fromkeys(w for a in assessments for w in a.warnings))


def _dominant_factor(
    assessments_per_segment: Sequence[Sequence[FactorAssessment]],
) -> str | None:
    """Factor with the highest mean score across segments (SPEC order
    breaks ties). Factors never scored are ignored."""
    totals: dict[str, list[float]] = {}
    for assessments in assessments_per_segment:
        for assessment in assessments:
            if assessment.available and assessment.score is not None:
                totals.setdefault(assessment.factor_id, []).append(assessment.score)
    best: str | None = None
    best_mean = -1.0
    for factor_id in SPEC_FACTORS:
        values = totals.get(factor_id)
        if not values:
            continue
        mean = sum(values) / len(values)
        if mean > best_mean:
            best_mean = mean
            best = factor_id
    return best
