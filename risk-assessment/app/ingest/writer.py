"""Atomic SQLite catalog writer (plan §8 step 6).

Writes ``thermal_climatology``, ``radiation_climatology``, ``meta`` and
``data_quality`` to a temp file then ``os.replace`` onto the target, so a
crash mid-write never leaves a half-built catalog. Re-running is
idempotent: the catalog is fully rebuilt from scratch each time.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.ingest.rad import RadiationRow
from app.ingest.rems import ThermalRow
from app.ingest.validate import IngestReport

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE thermal_climatology(
    sol INTEGER NOT NULL,
    hora INTEGER NOT NULL,
    air_temp_mean_K REAL,
    ground_temp_mean_K REAL,
    ground_temp_min_K REAL,
    ground_temp_max_K REAL,
    pressure_mean_Pa REAL,
    uv_abc_mean_W_m2 REAL,
    PRIMARY KEY (sol, hora)
);
CREATE TABLE radiation_climatology(
    sol INTEGER NOT NULL,
    hora INTEGER NOT NULL,
    dose_e_uGy_h REAL,
    dose_b_uGy_h REAL,
    unit TEXT,
    provenance TEXT,
    PRIMARY KEY (sol, hora)
);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE data_quality(dataset TEXT, period TEXT, note TEXT, severity TEXT);
"""

_THERMAL_COLUMNS = (
    "sol",
    "hora",
    "air_temp_mean_K",
    "ground_temp_mean_K",
    "ground_temp_min_K",
    "ground_temp_max_K",
    "pressure_mean_Pa",
    "uv_abc_mean_W_m2",
)

_RADIATION_COLUMNS = (
    "sol",
    "hora",
    "dose_e_uGy_h",
    "dose_b_uGy_h",
    "unit",
    "provenance",
)


def _thermal_params(row: ThermalRow) -> tuple[Any, ...]:
    return tuple(getattr(row, column) for column in _THERMAL_COLUMNS)


def _radiation_params(row: RadiationRow) -> tuple[Any, ...]:
    return tuple(getattr(row, column) for column in _RADIATION_COLUMNS)


def write_catalog(
    path: str | Path,
    *,
    thermal_rows: Iterable[ThermalRow],
    radiation_rows: Iterable[RadiationRow],
    meta: dict[str, Any],
    quality_rows: Iterable[tuple[str, str, str, str]],
) -> None:
    """Build the catalog at ``path`` atomically (temp file + rename)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        conn = sqlite3.connect(tmp_path)
        try:
            conn.executescript(_SCHEMA)
            conn.executemany(
                f"INSERT INTO thermal_climatology ({', '.join(_THERMAL_COLUMNS)})"
                f" VALUES ({', '.join('?' * len(_THERMAL_COLUMNS))})",
                (_thermal_params(row) for row in thermal_rows),
            )
            conn.executemany(
                f"INSERT INTO radiation_climatology ({', '.join(_RADIATION_COLUMNS)})"
                f" VALUES ({', '.join('?' * len(_RADIATION_COLUMNS))})",
                (_radiation_params(row) for row in radiation_rows),
            )
            conn.executemany(
                "INSERT INTO meta(key, value) VALUES (?, ?)",
                (
                    (key, json.dumps(value) if not isinstance(value, str) else value)
                    for key, value in meta.items()
                ),
            )
            conn.executemany(
                "INSERT INTO data_quality(dataset, period, note, severity) VALUES (?, ?, ?, ?)",
                quality_rows,
            )
            conn.commit()
        finally:
            conn.close()
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def report_to_quality_rows(reports: Iterable[IngestReport]) -> list[tuple[str, str, str, str]]:
    """Flatten ingest flags into ``data_quality`` rows."""
    rows: list[tuple[str, str, str, str]] = []
    for report in reports:
        for flag in report.flags:
            rows.append(
                (
                    flag["dataset"],
                    flag["period"],
                    flag["note"],
                    flag.get("severity", "info"),
                )
            )
        for reason, count in report.rejected.items():
            rows.append(
                (
                    report.dataset,
                    "all",
                    f"{count} row(s) rejected: {reason}",
                    "warning" if count else "info",
                )
            )
    return rows
