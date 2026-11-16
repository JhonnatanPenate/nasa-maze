"""Use case: risk assessment at a single point (SPEC §3.2/§4.2)."""

from app.core.application.environment_context import EnvironmentContextResolver
from app.core.application.factor_builder import (
    build_point_assessments,
    provenance_for,
    raster_factors_requested,
    terrain_requested,
    validate_factor_selection,
)
from app.core.domain.geo_point import GeoPoint
from app.core.domain.local_solar_time import validate_hour
from app.core.domain.risk_aggregator import aggregate
from app.core.errors.exceptions import DomainValidationError
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.features.point_assessment.domain.point_risk import (
    HourlyPointRisk,
    PointRisk,
)


class AssessPoint:
    """Gathers slope (MS4), raster bands (MS3) and environmental profiles
    (local catalog) for one point and aggregates the SPEC weighted risk.

    Phase 1: factor scores are pending (Phase 3), so ``risk`` is ``None``
    and ``level`` is ``unknown`` while ``available`` flags reflect real
    data coverage.
    """

    def __init__(
        self,
        terrain: TerrainSource,
        raster: RasterSource,
        env_resolver: EnvironmentContextResolver,
        weights: dict[str, float],
    ) -> None:
        self._terrain = terrain
        self._raster = raster
        self._env_resolver = env_resolver
        self._weights = weights

    def execute(
        self,
        point: GeoPoint,
        sol: int | None,
        hora: int | None,
        include_hourly: bool,
        factors: tuple[str, ...] | None,
    ) -> PointRisk:
        selected = validate_factor_selection(factors)
        hours = range(24) if hora is None else [self._validate_hora(hora)]

        # Terrain + raster reads are time-invariant: fetch once.
        slope_deg = self._terrain.slope_at(point) if terrain_requested(selected) else None
        band_values = self._raster.point_values(point) if raster_factors_requested(selected) else {}

        hourly: list[HourlyPointRisk] = []
        for hour in hours:
            context = self._env_resolver.resolve(sol, hour)
            assessments = build_point_assessments(
                factors=selected,
                slope_deg=slope_deg,
                band_values=band_values,
                context=context,
            )
            risk, level = aggregate(assessments, self._weights)
            hourly.append(
                HourlyPointRisk(
                    hora=hour,
                    risk=risk,
                    level=level,
                    factor_scores=assessments,
                )
            )

        worst = self._worst(hourly)
        context = self._env_resolver.resolve(sol, worst.hora)
        provenance = provenance_for(context)
        provenance["include_hourly"] = include_hourly
        return PointRisk(
            lat=point.lat,
            lon=point.lon,
            risk=worst.risk,
            level=worst.level,
            factor_scores=worst.factor_scores,
            sol=context.reference_sol,
            hora=worst.hora,
            provenance=provenance,
            by_hour=tuple(hourly) if include_hourly else None,
        )

    @staticmethod
    def _validate_hora(hora: int) -> int:
        try:
            return validate_hour(hora)
        except ValueError as exc:
            raise DomainValidationError(str(exc)) from exc

    @staticmethod
    def _worst(hourly: list[HourlyPointRisk]) -> HourlyPointRisk:
        """Worst case across hours: highest risk; ties/unscored -> first."""
        return max(
            hourly,
            key=lambda h: (
                h.risk is not None,
                h.risk if h.risk is not None else -1.0,
            ),
        )
