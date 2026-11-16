"""Use case: area risk aggregation (plan extension §7.1).

Evaluates the SPEC weighted risk on a regular grid covering the request
bbox — one ``slope_at`` (MS4) + one ``point_values`` (MS3) read per cell —
then aggregates level counts, blocked fraction, score statistics,
per-factor coverage and hotspots. It returns statistics only, never a
per-cell raster.

The grid pitch is the delivered ``rejilla`` resolution (~90 m,
``_GRID_RES_DEG``); ``cell_count``/``max_cells`` bound the request before
any upstream call. Environmental climatology is spatially uniform, so the
(sol, hora) context is resolved once and reused for every cell. Cells
outside upstream coverage count as ``unknown`` and are reported via
``uncovered_cells`` — missing data is never scored as safe. Vehicle-profile
restrictions feed ``blocked_fraction`` only; they never alter scores.

Cost is O(2 * cell_count) upstream point reads — area evaluation is meant
for modest bboxes; ``max_cells`` (default ``settings.max_area_cells``) is
the guard.
"""

import math

from app.core.application.environment_context import EnvironmentContextResolver
from app.core.application.factor_builder import (
    ScoringThresholds,
    build_point_assessments,
    coverage_confidence,
    provenance_for,
    sol_fallback_notes,
)
from app.core.domain.bounding_box import BoundingBox
from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.factor_catalog import SPEC_FACTORS
from app.core.domain.geo_point import GeoPoint
from app.core.domain.local_solar_time import validate_hour
from app.core.domain.restriction import evaluate_restrictions
from app.core.domain.risk_aggregator import aggregate
from app.core.domain.risk_level import RiskLevel
from app.core.domain.soil_type import classify_soil
from app.core.domain.tilt_model import TiltModelSet, predict_tilt
from app.core.errors.exceptions import (
    AreaTooLargeError,
    DomainValidationError,
    NoCoverageError,
)
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.core.ports.vehicle_profile_repository import VehicleProfileRepository
from app.features.area_assessment.domain.area_result import AreaResult

# Delivered rejilla grid pitch in degrees (~90 m at the Gale AOI latitude);
# Phase 0 inventory value, also used for the request cell-cap estimate.
GRID_RES_DEG = 0.0015183544372303697

_MAX_HOTSPOTS = 100
_HOT_LEVELS = (RiskLevel.HIGH, RiskLevel.CRITICAL)


class AssessArea:
    """Grid-aggregate SPEC risk over a bbox (additive plan extension)."""

    def __init__(
        self,
        terrain: TerrainSource,
        raster: RasterSource,
        env_resolver: EnvironmentContextResolver,
        vehicle_profiles: VehicleProfileRepository,
        distance_calculator: DistanceCalculator,
        weights: dict[str, float],
        thresholds: ScoringThresholds,
        tilt_models: TiltModelSet,
        model_version: str,
        default_vehicle_profile: str,
        max_area_cells: int,
    ) -> None:
        self._terrain = terrain
        self._raster = raster
        self._env_resolver = env_resolver
        self._vehicle_profiles = vehicle_profiles
        self._distance_calculator = distance_calculator
        self._weights = weights
        self._thresholds = thresholds
        self._tilt_models = tilt_models
        self._model_version = model_version
        self._default_vehicle_profile = default_vehicle_profile
        self._max_area_cells = max_area_cells

    def cell_count(self, bbox: BoundingBox) -> int:
        cols = math.ceil((bbox.max_lon - bbox.min_lon) / GRID_RES_DEG)
        rows = math.ceil((bbox.max_lat - bbox.min_lat) / GRID_RES_DEG)
        return cols * rows

    def check_cap(self, bbox: BoundingBox, max_cells: int | None) -> int:
        cap = self._max_area_cells if max_cells is None else int(max_cells)
        count = self.cell_count(bbox)
        if count > cap:
            raise AreaTooLargeError(f"Area spans ~{count} cells, exceeding max_cells={cap}")
        return count

    def execute(
        self,
        bbox: BoundingBox,
        sol: int | None,
        hora: int,
        vehicle_profile: str | None,
        max_cells: int | None,
    ) -> AreaResult:
        self.check_cap(bbox, max_cells)
        hour = self._validate_hora(hora)
        profile = self._vehicle_profiles.get(vehicle_profile or self._default_vehicle_profile)
        context = self._env_resolver.resolve(sol, hour)
        daily_predictors = self._env_resolver.daily_predictors(context)

        lons = self._axis(bbox.min_lon, bbox.max_lon)
        lats = self._axis(bbox.min_lat, bbox.max_lat)
        cell_size_m = self._cell_size_m(bbox)

        level_counts = {level.value: 0 for level in RiskLevel}
        factor_scored = dict.fromkeys(SPEC_FACTORS, 0)
        factor_missing = dict.fromkeys(SPEC_FACTORS, 0)
        factor_score_sums = dict.fromkeys(SPEC_FACTORS, 0.0)
        risks: list[float] = []
        hot_cells: list[tuple[float, float, float, str]] = []
        blocked = 0
        uncovered = 0
        conf_scored = 0
        conf_total = 0
        evaluated = 0

        temp_mean_K = (
            context.temperature.ground_temp_mean_K if context.temperature else None
        )

        for lat in lats:
            for lon in lons:
                point = GeoPoint(lat=lat, lon=lon)
                try:
                    slope_deg = self._terrain.slope_at(point)
                    band_values = self._raster.point_values(point)
                except NoCoverageError:
                    uncovered += 1
                    level_counts[RiskLevel.UNKNOWN.value] += 1
                    continue
                evaluated += 1

                soil = classify_soil(
                    rugosidad_m=band_values.get("rugosidad_m"),
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
                        "rugosidad": band_values.get("rugosidad_m"),
                        "inercia_termica_tiu": band_values.get("inercia_termica_tiu"),
                        "albedo": band_values.get("albedo"),
                    },
                    daily_predictors=daily_predictors,
                )
                restrictions = evaluate_restrictions(
                    profile,
                    slope_deg=slope_deg,
                    tilt=tilt,
                    temp_mean_K=temp_mean_K,
                )
                if any(r.blocking for r in restrictions):
                    blocked += 1

                assessments = build_point_assessments(
                    factors=SPEC_FACTORS,
                    slope_deg=slope_deg,
                    band_values=band_values,
                    context=context,
                    thresholds=self._thresholds,
                )
                risk, level = aggregate(assessments, self._weights)
                level_counts[level.value] += 1
                if risk is not None:
                    risks.append(risk)
                if level in _HOT_LEVELS and risk is not None:
                    hot_cells.append((risk, lat, lon, level.value))
                for assessment in assessments:
                    conf_total += 1
                    if assessment.available and assessment.score is not None:
                        conf_scored += 1
                        factor_scored[assessment.factor_id] += 1
                        factor_score_sums[assessment.factor_id] += assessment.score
                    else:
                        factor_missing[assessment.factor_id] += 1

        scored_risks = sorted(risks)
        mean_score = (
            sum(scored_risks) / len(scored_risks) if scored_risks else None
        )
        p95_score = (
            scored_risks[max(0, math.ceil(0.95 * len(scored_risks)) - 1)]
            if scored_risks
            else None
        )
        hot_cells.sort(key=lambda h: (-h[0], h[1], h[2]))
        hotspots: list[dict[str, object]] = [
            {"lat": lat, "lon": lon, "risk": risk, "level": level}
            for risk, lat, lon, level in hot_cells[:_MAX_HOTSPOTS]
        ]

        factor_stats = {
            factor_id: {
                "mean_score": (
                    factor_score_sums[factor_id] / factor_scored[factor_id]
                    if factor_scored[factor_id]
                    else None
                ),
                "scored_cells": factor_scored[factor_id],
                "available_fraction": (
                    factor_scored[factor_id] / evaluated if evaluated else 0.0
                ),
            }
            for factor_id in SPEC_FACTORS
        }

        notes = list(sol_fallback_notes([context]))
        for factor_id in SPEC_FACTORS:
            if factor_missing[factor_id] and evaluated:
                notes.append(
                    f"factor '{factor_id}' unavailable on "
                    f"{factor_missing[factor_id]}/{evaluated} cells"
                )
        if uncovered:
            notes.append(
                f"{uncovered} cells outside data coverage counted as unknown"
            )

        cell_count = len(lons) * len(lats)
        provenance = provenance_for(context, self._model_version)
        provenance["vehicle_profile"] = profile.name
        provenance["cell_size_m"] = round(cell_size_m, 3)
        provenance["grid_pitch_deg"] = GRID_RES_DEG

        return AreaResult(
            bbox=(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat),
            cell_count=cell_count,
            cell_size_m=cell_size_m,
            level_counts=level_counts,
            blocked_fraction=(blocked / evaluated if evaluated else None),
            mean_score=mean_score,
            p95_score=p95_score,
            factor_stats=factor_stats,
            hotspots=tuple(hotspots),
            uncovered_cells=uncovered,
            confidence=coverage_confidence(conf_scored, conf_total),
            provenance=provenance,
            data_quality_notes=tuple(notes),
            note=(
                f"Grid aggregation over {cell_count} cells "
                f"(~{cell_size_m:.0f} m pitch) at sol={context.reference_sol} "
                f"hora={hour}; vehicle_profile={profile.name}."
            ),
        )

    # -- internals ------------------------------------------------------

    @staticmethod
    def _axis(min_value: float, max_value: float) -> list[float]:
        """Sample positions from ``min_value`` stepping ``GRID_RES_DEG``;
        ``min + i*res < max`` holds for every generated index."""
        count = math.ceil((max_value - min_value) / GRID_RES_DEG)
        return [min_value + i * GRID_RES_DEG for i in range(count)]

    def _cell_size_m(self, bbox: BoundingBox) -> float:
        """Nominal cell pitch in meters at the bbox center (meridional +
        zonal spacing averaged — zonal shrinks with |lat| on Mars)."""
        center_lat = (bbox.min_lat + bbox.max_lat) / 2.0
        center_lon = (bbox.min_lon + bbox.max_lon) / 2.0
        pole_lat = min(center_lat + GRID_RES_DEG, 90.0)
        edge_lon = min(center_lon + GRID_RES_DEG, 180.0)
        d_lat = self._distance_calculator.distance_m(
            GeoPoint(center_lat, center_lon), GeoPoint(pole_lat, center_lon)
        )
        d_lon = self._distance_calculator.distance_m(
            GeoPoint(center_lat, center_lon),
            GeoPoint(center_lat, edge_lon),
        )
        return (d_lat + d_lon) / 2.0

    @staticmethod
    def _validate_hora(hora: int) -> int:
        try:
            return validate_hour(hora)
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc
