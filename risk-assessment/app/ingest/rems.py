"""REMS workbook reader -> ``thermal_climatology`` rows (plan §8 steps 1-4).

One row per ``(sol, hora_lmst)`` — the delivered workbook is a complete
2 sols x 24 h grid. Values are stored verbatim in their documented units
(K, Pa, W/m2); missing cells become NULL. No humidity column exists in
the delivered file (Phase 0 inventory).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.ingest.config_loader import WorkbookConfig
from app.ingest.validate import (
    PRESSURE_MAX_PA,
    PRESSURE_MIN_PA,
    TEMP_MAX_K,
    TEMP_MIN_K,
    IngestReport,
    UV_MIN_W_m2,
    check_finite_or_none,
    in_band,
)


@dataclass(frozen=True)
class ThermalRow:
    """One ``thermal_climatology`` record (canonical column names)."""

    sol: int
    hora: int
    air_temp_mean_K: float | None
    ground_temp_mean_K: float | None
    ground_temp_min_K: float | None
    ground_temp_max_K: float | None
    pressure_mean_Pa: float | None
    uv_abc_mean_W_m2: float | None


def _apply_conversion(value: Any, conversion: str | None) -> Any:
    if conversion == "int":
        return int(float(value))
    if conversion == "floor_int":
        return math.floor(float(value))
    return value


def read_rems(path: Path, config: WorkbookConfig) -> tuple[list[ThermalRow], IngestReport]:
    """Read + validate the REMS workbook; returns rows and a report."""
    report = IngestReport(dataset="rems")
    frame = pd.read_excel(path, sheet_name=config.sheet)

    # Resolve canonical -> source column using the configured mapping.
    key_by_canonical = {
        spec.canonical: (source, spec) for source, spec in config.key_columns.items()
    }
    value_by_canonical = {
        spec.canonical: (source, spec) for source, spec in config.value_columns.items()
    }
    missing = [c for c in ("sol", "hora") if c not in key_by_canonical]
    if missing:
        raise ValueError(
            f"REMS config lacks required key columns {missing} (mapped: {sorted(key_by_canonical)})"
        )

    sol_src, sol_spec = key_by_canonical["sol"]
    hora_src, hora_spec = key_by_canonical["hora"]

    rows: list[ThermalRow] = []
    seen: set[tuple[int, int]] = set()

    for _, record in frame.iterrows():
        report.rows_in += 1
        raw = record.to_dict()

        try:
            sol = int(_apply_conversion(raw[sol_src], sol_spec.conversion))
        except (TypeError, ValueError):
            report.reject("sol_not_int")
            continue
        try:
            hora = int(_apply_conversion(raw[hora_src], hora_spec.conversion))
        except (TypeError, ValueError):
            report.reject("hora_not_int")
            continue
        if sol <= 0:
            report.reject("sol_not_positive")
            continue
        if not 0 <= hora <= 23:
            report.reject("hora_out_of_range")
            continue
        if (sol, hora) in seen:
            report.reject("duplicate_key")
            continue

        values: dict[str, float | None] = {}
        bad = False
        for canonical, (source, _spec) in value_by_canonical.items():
            cell = check_finite_or_none(raw.get(source))
            values[canonical] = cell
            report.observe(canonical, cell)
            if (
                (
                    canonical
                    in {
                        "ground_temp_mean_K",
                        "ground_temp_min_K",
                        "ground_temp_max_K",
                        "air_temp_mean_K",
                    }
                    and not in_band(cell, TEMP_MIN_K, TEMP_MAX_K)
                )
                or (
                    canonical == "pressure_mean_Pa"
                    and not in_band(cell, PRESSURE_MIN_PA, PRESSURE_MAX_PA)
                )
                or (canonical == "uv_abc_mean_W_m2" and (cell is not None and cell < UV_MIN_W_m2))
            ):
                bad = True
        if bad:
            report.reject("sanity_band")
            continue

        seen.add((sol, hora))
        rows.append(
            ThermalRow(
                sol=sol,
                hora=hora,
                air_temp_mean_K=values.get("air_temp_mean_K"),
                ground_temp_mean_K=values.get("ground_temp_mean_K"),
                ground_temp_min_K=values.get("ground_temp_min_K"),
                ground_temp_max_K=values.get("ground_temp_max_K"),
                pressure_mean_Pa=values.get("pressure_mean_Pa"),
                uv_abc_mean_W_m2=values.get("uv_abc_mean_W_m2"),
            )
        )
        report.rows_kept += 1

    null_uv = sum(1 for r in rows if r.uv_abc_mean_W_m2 is None)
    if null_uv:
        report.flag(
            "all",
            f"uv_abc_mean_W_m2 is NULL in {null_uv} hourly rows (absent in the delivered workbook)",
        )
    sols = sorted({r.sol for r in rows})
    report.extras["sols"] = sols
    report.extras["hours_per_sol"] = {
        str(s): sorted(r.hora for r in rows if r.sol == s) for s in sols
    }
    return rows, report
