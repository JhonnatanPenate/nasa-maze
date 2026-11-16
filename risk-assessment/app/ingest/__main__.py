"""`python -m app.ingest` — offline workbook -> catalog pipeline (plan §8).

Builds ``risk_catalog.sqlite`` from the delivered REMS/RAD workbooks and
writes ``ingest_report.json`` next to it. With ``--seed-dir`` the catalog
(renamed ``risk_catalog_seed.sqlite``) and report are also copied there —
the committed seed copy used by Docker/offline runs.

    python -m app.ingest
    python -m app.ingest --rems x.xlsx --rad y.xlsx --out /tmp/cat.sqlite
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ingest.config_loader import load_environment_columns
from app.ingest.rad import read_rad
from app.ingest.rems import read_rems
from app.ingest.validate import IngestReport
from app.ingest.writer import SCHEMA_VERSION, report_to_quality_rows, write_catalog

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVICE_ROOT = _REPO_ROOT / "risk-assessment"

_DEFAULT_REMS = _REPO_ROOT / "data/gale/raw/ambiental/rems_resumen_horario.xlsx"
_DEFAULT_RAD = _REPO_ROOT / "data/gale/raw/ambiental/rad_dosis_observaciones.xlsx"
_DEFAULT_CONFIG = _SERVICE_ROOT / "config/environment_columns.yaml"
_DEFAULT_OUT = _REPO_ROOT / "data/processed/mars/risk/risk_catalog.sqlite"
_DEFAULT_SEED_DIR = _SERVICE_ROOT / "data/seed"
_SEED_CATALOG_NAME = "risk_catalog_seed.sqlite"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _report_dict(report: IngestReport, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows_in": report.rows_in,
        "rows_out": report.rows_kept,
        "rejected": report.rejected,
        "flags": report.flags,
        "ranges": {key: {"min": lo, "max": hi} for key, (lo, hi) in report.ranges.items()},
        "extras": report.extras,
        "source": source,
    }


def build(args: argparse.Namespace) -> int:
    started = datetime.now(UTC)
    rems_path = Path(args.rems)
    rad_path = Path(args.rad)
    config_path = Path(args.config)
    out = Path(args.out)
    report_path = Path(args.report) if args.report else out.parent / "ingest_report.json"

    for label, path in (("REMS", rems_path), ("RAD", rad_path), ("config", config_path)):
        if not path.is_file():
            print(f"error: {label} file not found: {path}", file=sys.stderr)
            return 2

    columns = load_environment_columns(config_path)

    thermal_rows, rems_report = read_rems(rems_path, columns.rems)
    radiation_rows, rad_report = read_rad(rad_path, columns.rad)

    built_at = datetime.now(UTC)
    meta: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "built_at": built_at.isoformat(),
        "catalog_version": f"{built_at:%Y-%m-%d}.{built_at:%H%M%S}",
        "rems_source": str(rems_path),
        "rems_sha256": _sha256(rems_path),
        "rems_sheet": columns.rems.sheet,
        "rems_rows": len(thermal_rows),
        "rad_source": str(rad_path),
        "rad_sha256": _sha256(rad_path),
        "rad_sheet": columns.rad.sheet,
        "rad_rows": len(radiation_rows),
        "units": {
            "thermal": {
                "air_temp_mean_K": "K",
                "ground_temp_mean_K": "K",
                "ground_temp_min_K": "K",
                "ground_temp_max_K": "K",
                "pressure_mean_Pa": "Pa",
                "uv_abc_mean_W_m2": "W/m2",
            },
            "radiation": {
                "dose_e_uGy_h": "uGy/h",
                "dose_b_uGy_h": "uGy/h",
            },
        },
        "bin_config": {
            "key": "(sol, hora) integer LMST hour bin",
            "rad_hora_bin": "floor(hora_lmst)",
            "rad_channel": columns.rad.selected_channel or "dose_e_uGy_h",
            "rad_filter": f"dose_e >= {0.7} * per-sol median",
            "rad_empty_hour": "per-sol mean of filtered dose-E observations",
            "sol_selection": "nearest available sol per dataset, ties -> lower",
        },
        "coordinate_system": "IAU_2015:49900 (planetocentric deg, R=3396190 m)",
    }

    quality_rows = report_to_quality_rows([rems_report, rad_report])
    write_catalog(
        out,
        thermal_rows=thermal_rows,
        radiation_rows=radiation_rows,
        meta=meta,
        quality_rows=quality_rows,
    )

    report: dict[str, Any] = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "out": str(out),
        "report": str(report_path),
        "seed_dir": str(Path(args.seed_dir)) if args.seed_dir else None,
        "datasets": {
            "rems": _report_dict(
                rems_report,
                {
                    "path": str(rems_path),
                    "sha256": _sha256(rems_path),
                    "sheet": columns.rems.sheet,
                },
            ),
            "rad": _report_dict(
                rad_report,
                {
                    "path": str(rad_path),
                    "sha256": _sha256(rad_path),
                    "sheet": columns.rad.sheet,
                },
            ),
        },
        "tables": {
            "thermal_climatology": len(thermal_rows),
            "radiation_climatology": len(radiation_rows),
            "meta": len(meta),
            "data_quality": len(quality_rows),
        },
    }
    if args.seed_dir:
        seed_dir = Path(args.seed_dir)
        seed_dir.mkdir(parents=True, exist_ok=True)
        report["seed_copied"] = [
            str(seed_dir / _SEED_CATALOG_NAME),
            str(seed_dir / "ingest_report.json"),
        ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.seed_dir:
        seed_dir = Path(args.seed_dir)
        shutil.copy2(out, seed_dir / _SEED_CATALOG_NAME)
        shutil.copy2(report_path, seed_dir / "ingest_report.json")

    total_rejected = sum(count for r in (rems_report, rad_report) for count in r.rejected.values())
    print(
        f"catalog -> {out} "
        f"(thermal={len(thermal_rows)}, radiation={len(radiation_rows)}, "
        f"rejected={total_rejected})"
    )
    print(f"report  -> {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.ingest",
        description="Build risk_catalog.sqlite from REMS/RAD workbooks (offline).",
    )
    parser.add_argument("--rems", default=str(_DEFAULT_REMS), help="REMS .xlsx path")
    parser.add_argument("--rad", default=str(_DEFAULT_RAD), help="RAD .xlsx path")
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help="environment_columns.yaml path",
    )
    parser.add_argument(
        "--out",
        default=str(_DEFAULT_OUT),
        help="output catalog path (default data/processed/mars/risk/)",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="ingest_report.json path (default: <out dir>/ingest_report.json)",
    )
    parser.add_argument(
        "--seed-dir",
        default=str(_DEFAULT_SEED_DIR),
        help="also copy catalog+report here (default risk-assessment/data/seed/)",
    )
    args = parser.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
