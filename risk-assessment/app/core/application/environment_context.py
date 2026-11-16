"""Shared resolver: request (sol, hora) -> selected environmental profiles.

Selects the nearest available sol **independently per dataset** (SPEC §3.1:
REMS covers sols {1360, 2140}, RAD {1360, 2140, 3290, 4710}) and echoes the
reference sol plus the actually-selected sols for provenance.
"""

from dataclasses import dataclass

from app.core.errors.exceptions import DomainValidationError
from app.core.ports.environment_repository import (
    EnvironmentRepository,
    RadiationReading,
    TemperatureReading,
)


@dataclass(frozen=True)
class EnvironmentalContext:
    """Resolved environmental inputs for one (sol, hora) request."""

    reference_sol: int
    hora: int
    rems_sol: int | None
    rad_sol: int | None
    temperature: TemperatureReading | None
    radiation: RadiationReading | None


class EnvironmentContextResolver:
    def __init__(
        self,
        repository: EnvironmentRepository,
        default_sol: int,
    ) -> None:
        self._repository = repository
        self._default_sol = default_sol

    def resolve(self, sol: int | None, hora: int) -> EnvironmentalContext:
        reference = self._default_sol if sol is None else sol
        try:
            reference_int = int(reference)
        except (TypeError, ValueError, OverflowError) as exc:
            raise DomainValidationError(f"sol must be an integer, got {sol!r}") from exc
        if isinstance(reference, bool) or reference_int != reference:
            raise DomainValidationError(f"sol must be an integer, got {sol!r}")
        rems_sol = self._repository.nearest_sol("rems", reference_int)
        rad_sol = self._repository.nearest_sol("rad", reference_int)
        temperature = (
            self._repository.temperature_at(rems_sol, hora) if rems_sol is not None else None
        )
        radiation = self._repository.radiation_at(rad_sol, hora) if rad_sol is not None else None
        return EnvironmentalContext(
            reference_sol=reference_int,
            hora=hora,
            rems_sol=rems_sol,
            rad_sol=rad_sol,
            temperature=temperature,
            radiation=radiation,
        )

    def daily_predictors(self, context: EnvironmentalContext) -> dict[str, float]:
        """Per-selected-sol daily means for the tilt model (Javi
        ``predictores_diarios``): ``temp_suelo_K_media`` from the REMS sol's
        hourly ground means and ``dosis_rad_uGy_h`` from the RAD sol's
        hourly dose-E rates. Missing hours are skipped; empty -> key absent
        (``predict_tilt`` then applies Javi's 0.0 default before clipping).
        """
        predictors: dict[str, float] = {}
        if context.rems_sol is not None:
            temps = [
                reading.ground_temp_mean_K
                for reading in (
                    self._repository.temperature_at(context.rems_sol, hora)
                    for hora in range(24)
                )
                if reading is not None and reading.ground_temp_mean_K is not None
            ]
            if temps:
                predictors["temp_suelo_K_media"] = sum(temps) / len(temps)
        if context.rad_sol is not None:
            doses = [
                reading.dose_e_uGy_h
                for reading in (
                    self._repository.radiation_at(context.rad_sol, hora)
                    for hora in range(24)
                )
                if reading is not None and reading.dose_e_uGy_h is not None
            ]
            if doses:
                predictors["dosis_rad_uGy_h"] = sum(doses) / len(doses)
        return predictors
