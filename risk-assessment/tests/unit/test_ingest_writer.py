"""Catalog writer tests: atomic write, schema, idempotency."""

import sqlite3
from pathlib import Path

from app.ingest.rad import RadiationRow
from app.ingest.rems import ThermalRow
from app.ingest.validate import IngestReport
from app.ingest.writer import report_to_quality_rows, write_catalog


def _thermal() -> list[ThermalRow]:
    return [
        ThermalRow(
            sol=1360,
            hora=9,
            air_temp_mean_K=231.7,
            ground_temp_mean_K=246.7,
            ground_temp_min_K=239.7,
            ground_temp_max_K=253.2,
            pressure_mean_Pa=757.4,
            uv_abc_mean_W_m2=None,
        )
    ]


def _radiation() -> list[RadiationRow]:
    return [
        RadiationRow(
            sol=1360,
            hora=9,
            dose_e_uGy_h=10.66,
            dose_b_uGy_h=10.36,
            unit="uGy/hour",
            provenance="hourly_mean",
        ),
        RadiationRow(
            sol=1360,
            hora=7,
            dose_e_uGy_h=10.66,
            dose_b_uGy_h=10.36,
            unit="uGy/hour",
            provenance="sol_mean_fallback",
        ),
    ]


def _meta() -> dict:
    return {"schema_version": "1", "built_at": "2026-11-16T00:00:00+00:00"}


def test_write_catalog_tables(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "risk_catalog.sqlite"
    write_catalog(
        out,
        thermal_rows=_thermal(),
        radiation_rows=_radiation(),
        meta=_meta(),
        quality_rows=[("rad", "sol 1360", "fallback hours 6-9", "info")],
    )
    assert out.is_file()
    conn = sqlite3.connect(out)
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert {
        "thermal_climatology",
        "radiation_climatology",
        "meta",
        "data_quality",
    } <= tables
    assert conn.execute("SELECT COUNT(*) FROM thermal_climatology").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM radiation_climatology").fetchone()[0] == 2
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    assert meta["schema_version"] == "1"
    assert meta["built_at"] == "2026-11-16T00:00:00+00:00"
    dq = conn.execute("SELECT * FROM data_quality").fetchall()
    assert dq == [("rad", "sol 1360", "fallback hours 6-9", "info")]
    conn.close()


def test_atomic_no_temp_files_left(tmp_path: Path) -> None:
    out = tmp_path / "risk_catalog.sqlite"
    write_catalog(
        out,
        thermal_rows=_thermal(),
        radiation_rows=_radiation(),
        meta=_meta(),
        quality_rows=[],
    )
    assert list(tmp_path.glob("*.tmp")) == []
    assert not list(tmp_path.glob("risk_catalog.sqlite.*"))


def test_idempotent_rebuild(tmp_path: Path) -> None:
    out = tmp_path / "risk_catalog.sqlite"
    for _ in range(2):
        write_catalog(
            out,
            thermal_rows=_thermal(),
            radiation_rows=_radiation(),
            meta=_meta(),
            quality_rows=[],
        )
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM radiation_climatology").fetchone()[0] == 2
    conn.close()


def test_report_to_quality_rows() -> None:
    rems = IngestReport(dataset="rems")
    rems.flag("all", "uv nulls", "info")
    rad = IngestReport(dataset="rad")
    rad.reject("dose_negative")
    rad.reject("dose_negative")
    rows = report_to_quality_rows([rems, rad])
    assert ("rems", "all", "uv nulls", "info") in rows
    assert ("rad", "all", "2 row(s) rejected: dose_negative", "warning") in rows
