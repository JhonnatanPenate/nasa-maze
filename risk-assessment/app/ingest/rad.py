"""RAD workbook reader -> ``radiation_climatology`` rows (plan §8 steps 1-6).

Pipeline per plan §8:
1. validate observations (sol, fractional ``hora_lmst`` in [0, 24),
   non-negative ``dosis_e_uGy_h`` — the SPEC channel; dose-B is kept for
   provenance only and never combined);
2. per-sol background filter ``dose_e >= 0.7 * median(dose_e)``
   (Javi's optimizer rule — NOT an SEP/alert threshold);
3. bin by ``floor(hora_lmst)`` and take the hourly mean;
4. empty hour bins inside a valid sol get the per-sol mean fallback,
   flagged ``provenance='sol_mean_fallback'`` (never invented silently).

Duplicate ``(sol, hora_lmst)`` timestamps are tolerated — they are distinct
observations and simply both enter the hourly mean (Phase 0 inventory).
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.ingest.config_loader import WorkbookConfig
from app.ingest.validate import (
    HORA_MAX,
    HORA_MIN,
    RAD_KEEP_FRACTION,
    DOSE_MIN_Ugy_h,
    IngestReport,
    check_finite_or_none,
)

PROVENANCE_HOURLY_MEAN = "hourly_mean"
PROVENANCE_SOL_MEAN_FALLBACK = "sol_mean_fallback"


@dataclass(frozen=True)
class RadiationRow:
    """One ``radiation_climatology`` record."""

    sol: int
    hora: int
    dose_e_uGy_h: float | None
    dose_b_uGy_h: float | None
    unit: str | None
    provenance: str


@dataclass(frozen=True)
class _Observation:
    sol: int
    hora_lmst: float
    dose_e: float
    dose_b: float | None
    unit: str | None


def _column_lookup(config: WorkbookConfig) -> dict[str, tuple[str, Any]]:
    """canonical -> (source_column, spec) across key+value+unit mappings."""
    lookup: dict[str, tuple[str, Any]] = {}
    for group in (
        config.key_columns,
        config.value_columns,
        config.unit_column,
    ):
        for source, spec in group.items():
            lookup[spec.canonical] = (source, spec)
    return lookup


def read_rad(path: Path, config: WorkbookConfig) -> tuple[list[RadiationRow], IngestReport]:
    """Read + filter + aggregate the RAD workbook."""
    report = IngestReport(dataset="rad")
    frame = pd.read_excel(path, sheet_name=config.sheet)
    lookup = _column_lookup(config)

    def source_for(canonical: str) -> str | None:
        entry = lookup.get(canonical)
        return entry[0] if entry else None

    sol_src = source_for("sol")
    hora_src = source_for("hora")
    dose_e_src = source_for(config.selected_channel or "dose_e_uGy_h")
    dose_b_src = source_for("dose_b_uGy_h")
    unit_src = source_for("unit_original")
    missing = [
        name
        for name, src in (
            ("sol", sol_src),
            ("hora", hora_src),
            ("dose_e", dose_e_src),
        )
        if src is None
    ]
    if missing:
        raise ValueError(f"RAD config lacks required columns {missing}")

    observations: list[_Observation] = []
    units: set[str] = set()
    timestamps: set[tuple[int, float]] = set()
    duplicate_timestamps = 0

    for _, record in frame.iterrows():
        report.rows_in += 1
        raw = record.to_dict()

        sol_raw = raw.get(sol_src)
        try:
            sol_f = float(sol_raw)
        except (TypeError, ValueError):
            report.reject("sol_not_int")
            continue
        if not math.isfinite(sol_f) or sol_f != math.floor(sol_f):
            report.reject("sol_not_int")
            continue
        sol = int(sol_f)
        if sol <= 0:
            report.reject("sol_not_positive")
            continue

        hora_raw = check_finite_or_none(raw.get(hora_src))
        if hora_raw is None or not HORA_MIN <= hora_raw < HORA_MAX:
            report.reject("hora_out_of_range")
            continue

        dose_e = check_finite_or_none(raw.get(dose_e_src))
        if dose_e is None:
            report.reject("dose_e_missing")
            continue
        if dose_e < DOSE_MIN_Ugy_h:
            report.reject("dose_negative")
            continue
        report.observe("dose_e_uGy_h", dose_e)

        dose_b = check_finite_or_none(raw.get(dose_b_src)) if dose_b_src else None
        if dose_b is not None and dose_b < DOSE_MIN_Ugy_h:
            report.reject("dose_b_negative")
            continue
        if dose_b is not None:
            report.observe("dose_b_uGy_h", dose_b)

        unit_raw = raw.get(unit_src) if unit_src else None
        unit = str(unit_raw) if unit_raw is not None else None
        if unit:
            units.add(unit)

        key = (sol, hora_raw)
        if key in timestamps:
            duplicate_timestamps += 1
        timestamps.add(key)

        observations.append(
            _Observation(
                sol=sol,
                hora_lmst=hora_raw,
                dose_e=dose_e,
                dose_b=dose_b,
                unit=unit,
            )
        )

    if duplicate_timestamps:
        report.flag(
            "all",
            f"{duplicate_timestamps} duplicate (sol, hora_lmst) timestamps "
            "tolerated; both observations enter the hourly mean",
        )
    if len(units) > 1:
        report.flag(
            "all",
            f"mixed unidad_original values {sorted(units)}; dose assumed uGy/h per delivered data",
            severity="warning",
        )
    report.extras["units"] = sorted(units)

    # --- per-sol background filter + hourly aggregation -----------------
    by_sol: dict[int, list[_Observation]] = defaultdict(list)
    for obs in observations:
        by_sol[obs.sol].append(obs)

    rows: list[RadiationRow] = []
    fallback_hours: dict[str, list[int]] = {}
    filtered_counts: dict[str, dict[str, float]] = {}

    for sol in sorted(by_sol):
        sol_obs = by_sol[sol]
        median_e = statistics.median(o.dose_e for o in sol_obs)
        threshold = RAD_KEEP_FRACTION * median_e
        kept = [o for o in sol_obs if o.dose_e >= threshold]
        filtered_counts[str(sol)] = {
            "observations": len(sol_obs),
            "kept_after_filter": len(kept),
            "median_dose_e": median_e,
            "filter_threshold": threshold,
        }
        if not kept:
            report.reject(f"sol_{sol}_all_filtered")
            continue

        bins: dict[int, list[_Observation]] = defaultdict(list)
        for obs in kept:
            bins[math.floor(obs.hora_lmst)].append(obs)

        sol_mean_e = statistics.fmean(o.dose_e for o in kept)
        sol_mean_b_values = [o.dose_b for o in kept if o.dose_b is not None]
        sol_mean_b = statistics.fmean(sol_mean_b_values) if sol_mean_b_values else None
        fallback: list[int] = []

        for hora in range(24):
            bin_obs = bins.get(hora, [])
            unit = bin_obs[0].unit if bin_obs else (kept[0].unit)
            if bin_obs:
                dose_e = statistics.fmean(o.dose_e for o in bin_obs)
                dose_b_values = [o.dose_b for o in bin_obs if o.dose_b is not None]
                dose_b = statistics.fmean(dose_b_values) if dose_b_values else None
                provenance = PROVENANCE_HOURLY_MEAN
            else:
                dose_e = sol_mean_e
                dose_b = sol_mean_b
                provenance = PROVENANCE_SOL_MEAN_FALLBACK
                fallback.append(hora)
            rows.append(
                RadiationRow(
                    sol=sol,
                    hora=hora,
                    dose_e_uGy_h=dose_e,
                    dose_b_uGy_h=dose_b,
                    unit=unit,
                    provenance=provenance,
                )
            )
            report.rows_kept += 1

        if fallback:
            fallback_hours[str(sol)] = fallback
            report.flag(
                f"sol {sol}",
                f"hours {fallback} have no observations after filtering; "
                "per-sol mean fallback applied (Javi empty-bin rule)",
            )

    report.extras["sols"] = sorted(by_sol)
    report.extras["filtered"] = filtered_counts
    report.extras["fallback_hours"] = fallback_hours
    report.extras["duplicate_timestamps"] = duplicate_timestamps
    return rows, report
