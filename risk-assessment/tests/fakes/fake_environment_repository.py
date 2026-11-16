"""Dict-backed fake EnvironmentRepository for tests.

``rems``/``rad`` map ``(sol, hora)`` -> reading; sols are derived from the
keys so nearest-sol selection behaves like the SQLite repository.
"""

from app.core.ports.environment_repository import (
    EnvironmentDataset,
    RadiationReading,
    TemperatureReading,
)


class FakeEnvironmentRepository:
    def __init__(
        self,
        rems: dict[tuple[int, int], TemperatureReading] | None = None,
        rad: dict[tuple[int, int], RadiationReading] | None = None,
    ) -> None:
        self._rems = rems or {}
        self._rad = rad or {}

    def ping(self) -> bool:
        return bool(self._rems or self._rad)

    def available_sols(self, dataset: EnvironmentDataset) -> tuple[int, ...]:
        table = self._rems if dataset == "rems" else self._rad
        return tuple(sorted({sol for sol, _hora in table}))

    def nearest_sol(self, dataset: EnvironmentDataset, sol: int) -> int | None:
        sols = self.available_sols(dataset)
        if not sols:
            return None
        return min(sols, key=lambda s: (abs(s - sol), s))

    def temperature_at(self, sol: int, hora: int) -> TemperatureReading | None:
        return self._rems.get((sol, hora))

    def radiation_at(self, sol: int, hora: int) -> RadiationReading | None:
        return self._rad.get((sol, hora))
