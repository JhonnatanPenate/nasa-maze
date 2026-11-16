"""Real-workbook ingest: `python -m app.ingest` end-to-end (plan §11 P2).

Builds the catalog from the delivered REMS/RAD files into tmp dirs and
verifies the repository returns Javi-compatible hourly profiles with
provenance. Skipped when the delivered workbooks are absent.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from app.infrastructure.repositories.sqlite_environment_repository import (
    SqliteEnvironmentRepository,
)
from app.ingest.__main__ import _DEFAULT_RAD, _DEFAULT_REMS, main

pytestmark = pytest.mark.skipif(
    not (_DEFAULT_REMS.is_file() and _DEFAULT_RAD.is_file()),
    reason="delivered REMS/RAD workbooks not present",
)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[Path, Path]:
    tmp = tmp_path_factory.mktemp("ingest")
    out = tmp / "risk_catalog.sqlite"
    report = tmp / "ingest_report.json"
    seed = tmp / "seed"
    rc = main(
        [
            "--out",
            str(out),
            "--report",
            str(report),
            "--seed-dir",
            str(seed),
        ]
    )
    assert rc == 0
    return out, report


def test_catalog_row_counts(built) -> None:  # type: ignore[no-untyped-def]
    out, _ = built
    conn = sqlite3.connect(out)
    thermal = conn.execute("SELECT COUNT(*) FROM thermal_climatology").fetchone()[0]
    radiation = conn.execute("SELECT COUNT(*) FROM radiation_climatology").fetchone()[0]
    conn.close()
    # 2 REMS sols x 24 h; 4 RAD sols x 24 h (fallback fills gaps).
    assert thermal == 48
    assert radiation == 96


def test_repository_profiles(built) -> None:  # type: ignore[no-untyped-def]
    out, _ = built
    repo = SqliteEnvironmentRepository(str(out))
    assert repo.ping() is True
    assert repo.available_sols("rems") == (1360, 2140)
    assert repo.available_sols("rad") == (1360, 2140, 3290, 4710)

    temp = repo.temperature_at(1360, 9)
    assert temp is not None
    assert temp.air_temp_mean_K is not None
    assert 123.15 <= temp.air_temp_mean_K <= 323.15

    rad = repo.radiation_at(1360, 9)
    assert rad is not None
    assert rad.dose_e_uGy_h is not None and rad.dose_e_uGy_h > 0
    assert rad.unit == "uGy/hour"
    # sol 1360 has no observations at LMST 6-9 -> fallback provenance.
    fallback = repo.radiation_at(1360, 7)
    assert fallback is not None
    assert fallback.provenance == "sol_mean_fallback"
    observed = repo.radiation_at(1360, 12)
    assert observed is not None
    assert observed.provenance == "hourly_mean"

    # Independent nearest-sol selection per dataset.
    assert repo.nearest_sol("rems", 5000) == 2140
    assert repo.nearest_sol("rad", 5000) == 4710


def test_ingest_report_clean(built) -> None:  # type: ignore[no-untyped-def]
    _, report_path = built
    report = json.loads(report_path.read_text())
    rems = report["datasets"]["rems"]
    rad = report["datasets"]["rad"]
    # No unexplained rejected rows on the delivered workbooks.
    assert rems["rejected"] == {}
    assert rad["rejected"] == {}
    assert rems["rows_in"] == rems["rows_out"] == 48
    assert rad["rows_in"] == 350
    # Known Phase 0 findings are flagged, not silent.
    assert rad["extras"]["fallback_hours"].get("1360") == [6, 7, 8, 9]
    assert rad["extras"]["duplicate_timestamps"] == 1
    assert any("uv_abc" in f["note"] for f in rems["flags"])
    # Source hashes recorded.
    assert len(rems["source"]["sha256"]) == 64
    assert len(rad["source"]["sha256"]) == 64


def test_seed_copy_written(built, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _, report_path = built
    # The fixture wrote seed into its own tmp dir; verify via report.
    report = json.loads(report_path.read_text())
    assert report["seed_copied"]
    seed_catalog = Path(report["seed_copied"][0])
    assert seed_catalog.name == "risk_catalog_seed.sqlite"
    assert seed_catalog.is_file()
    conn = sqlite3.connect(seed_catalog)
    assert conn.execute("SELECT COUNT(*) FROM thermal_climatology").fetchone()[0] == 48
    conn.close()


def test_idempotent_second_run(built, tmp_path) -> None:  # type: ignore[no-untyped-def]
    out, report_path = built
    rc = main(
        [
            "--out",
            str(out),
            "--report",
            str(report_path),
            "--seed-dir",
            str(tmp_path / "seed2"),
        ]
    )
    assert rc == 0
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM thermal_climatology").fetchone()[0] == 48
    assert conn.execute("SELECT COUNT(*) FROM radiation_climatology").fetchone()[0] == 96
    conn.close()
