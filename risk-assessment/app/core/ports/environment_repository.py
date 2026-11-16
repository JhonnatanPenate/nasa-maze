"""Port: environmental climatology (REMS temperature + RAD dose-E).

Backed by the local SQLite catalog built by `python -m app.ingest`
(plan §8). All lookups are keyed by integer sol + LMST hour bin; the
repository selects/echoes the nearest available sol per dataset.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

EnvironmentDataset = Literal["rems", "rad"]


@dataclass(frozen=True)
class TemperatureReading:
    """Hourly REMS profile at (sol, hora). Units per config mapping:
    Kelvin, Pascals, W/m2. ``None`` fields were absent in the workbook."""

    sol: int
    hora: int
    air_temp_mean_K: float | None
    ground_temp_mean_K: float | None
    ground_temp_min_K: float | None
    ground_temp_max_K: float | None
    pressure_mean_Pa: float | None
    uv_abc_mean_W_m2: float | None


@dataclass(frozen=True)
class RadiationReading:
    """Hourly RAD dose-rate profile at (sol, hora). ``dose_e_uGy_h`` is
    the SPEC channel (uGy/h); dose-B is kept for provenance only and is
    never combined with dose-E."""

    sol: int
    hora: int
    dose_e_uGy_h: float | None
    dose_b_uGy_h: float | None
    unit: str | None


class EnvironmentRepository(Protocol):
    """Climatology lookups. Implementations: SqliteEnvironmentRepository,
    UnavailableEnvironmentRepository (tests also use fakes)."""

    def ping(self) -> bool:
        """True when a readable catalog is loaded."""
        ...

    def available_sols(self, dataset: EnvironmentDataset) -> tuple[int, ...]:
        """Sols with coverage for ``dataset``, ascending."""
        ...

    def nearest_sol(self, dataset: EnvironmentDataset, sol: int) -> int | None:
        """Nearest available sol to ``sol`` for ``dataset`` (ties -> lower
        sol), or None when the dataset has no coverage."""
        ...

    def temperature_at(self, sol: int, hora: int) -> TemperatureReading | None:
        """REMS hourly profile at exactly (sol, hora); None when absent."""
        ...

    def radiation_at(self, sol: int, hora: int) -> RadiationReading | None:
        """RAD hourly profile at exactly (sol, hora); None when absent."""
        ...
