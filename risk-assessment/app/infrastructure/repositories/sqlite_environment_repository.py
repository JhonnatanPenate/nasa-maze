"""SQLite-backed environmental climatology repository (read-only).

Reads the catalog built by `python -m app.ingest` (plan §8). The service
opens it with ``mode=ro`` and never writes. Expected schema (Phase 2):

    thermal_climatology(sol INTEGER, hora INTEGER,
        air_temp_mean_K, ground_temp_mean_K, ground_temp_min_K,
        ground_temp_max_K, pressure_mean_Pa, uv_abc_mean_W_m2 REAL)
    radiation_climatology(sol INTEGER, hora INTEGER,
        dose_e_uGy_h, dose_b_uGy_h REAL, unit TEXT, provenance TEXT)
    meta(key TEXT PRIMARY KEY, value TEXT)
    data_quality(dataset TEXT, period TEXT, note TEXT, severity TEXT)

Until Phase 2 ships the catalog, missing tables simply yield no coverage
(factors report ``available: false``) rather than errors.
"""

import sqlite3
from pathlib import Path

from app.core.errors.exceptions import ClimatologyUnavailableError
from app.core.ports.environment_repository import (
    EnvironmentDataset,
    RadiationReading,
    TemperatureReading,
)


class SqliteEnvironmentRepository:
    def __init__(self, catalog_path: str) -> None:
        self._path = catalog_path
        self._connection: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._connection is None:
            path = Path(self._path)
            if not path.is_file():
                raise ClimatologyUnavailableError(f"Environmental catalog not found: {self._path}")
            try:
                self._connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                self._connection.row_factory = sqlite3.Row
            except sqlite3.Error as exc:
                raise ClimatologyUnavailableError(
                    f"Cannot open environmental catalog {self._path}: {exc}"
                ) from exc
        return self._connection

    def ping(self) -> bool:
        try:
            conn = self._connect()
            conn.execute("SELECT 1").fetchone()
            return True
        except (ClimatologyUnavailableError, sqlite3.Error):
            return False

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    def available_sols(self, dataset: EnvironmentDataset) -> tuple[int, ...]:
        table = _TABLE_BY_DATASET[dataset]
        try:
            conn = self._connect()
        except ClimatologyUnavailableError:
            return ()
        if not self._table_exists(conn, table):
            return ()
        try:
            rows = conn.execute(f"SELECT DISTINCT sol FROM {table} ORDER BY sol").fetchall()
        except sqlite3.Error:
            return ()
        return tuple(int(row["sol"]) for row in rows)

    def nearest_sol(self, dataset: EnvironmentDataset, sol: int) -> int | None:
        sols = self.available_sols(dataset)
        if not sols:
            return None
        # Ties resolve to the lower sol (deterministic).
        return min(sols, key=lambda s: (abs(s - sol), s))

    def temperature_at(self, sol: int, hora: int) -> TemperatureReading | None:
        try:
            conn = self._connect()
        except ClimatologyUnavailableError:
            return None
        if not self._table_exists(conn, "thermal_climatology"):
            return None
        try:
            row = conn.execute(
                "SELECT * FROM thermal_climatology WHERE sol=? AND hora=?",
                (sol, hora),
            ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        return TemperatureReading(
            sol=int(row["sol"]),
            hora=int(row["hora"]),
            air_temp_mean_K=row["air_temp_mean_K"],
            ground_temp_mean_K=row["ground_temp_mean_K"],
            ground_temp_min_K=row["ground_temp_min_K"],
            ground_temp_max_K=row["ground_temp_max_K"],
            pressure_mean_Pa=row["pressure_mean_Pa"],
            uv_abc_mean_W_m2=row["uv_abc_mean_W_m2"],
        )

    def radiation_at(self, sol: int, hora: int) -> RadiationReading | None:
        try:
            conn = self._connect()
        except ClimatologyUnavailableError:
            return None
        if not self._table_exists(conn, "radiation_climatology"):
            return None
        try:
            row = conn.execute(
                "SELECT * FROM radiation_climatology WHERE sol=? AND hora=?",
                (sol, hora),
            ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        keys = set(row.keys())
        return RadiationReading(
            sol=int(row["sol"]),
            hora=int(row["hora"]),
            dose_e_uGy_h=row["dose_e_uGy_h"],
            dose_b_uGy_h=row["dose_b_uGy_h"],
            unit=row["unit"],
            provenance=row["provenance"] if "provenance" in keys else None,
        )


_TABLE_BY_DATASET: dict[EnvironmentDataset, str] = {
    "rems": "thermal_climatology",
    "rad": "radiation_climatology",
}
