"""Environment repository used when no catalog file exists.

Reports no coverage: every lookup returns empty/None so the
SPEC factors degrade to ``available: false`` instead of failing.
"""

from app.core.ports.environment_repository import (
    EnvironmentDataset,
    RadiationReading,
    TemperatureReading,
)


class UnavailableEnvironmentRepository:
    def ping(self) -> bool:
        return False

    def available_sols(self, dataset: EnvironmentDataset) -> tuple[int, ...]:
        return ()

    def nearest_sol(self, dataset: EnvironmentDataset, sol: int) -> int | None:
        return None

    def temperature_at(self, sol: int, hora: int) -> TemperatureReading | None:
        return None

    def radiation_at(self, sol: int, hora: int) -> RadiationReading | None:
        return None
