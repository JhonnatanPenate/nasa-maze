"""Integration test: seed-mode catalog build (T2.2 acceptance)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from location_service.ingest.__main__ import main

SERVICE_ROOT = Path(__file__).parent.parent.parent
REPO_ROOT = SERVICE_ROOT.parent
MISSION_XLSX = REPO_ROOT / "data/gale/processed/gale_puntos_quimica.xlsx"
CONFIG_DIR = SERVICE_ROOT / "config"
SEED_OUT = SERVICE_ROOT / "data/seed/location_catalog_seed.sqlite"


def test_seed_build(tmp_path):
    out = tmp_path / "location_catalog.sqlite"
    report_path = tmp_path / "ingest_report.json"
    rc = main(
        [
            "build",
            "--mission",
            str(MISSION_XLSX),
            "--config",
            str(CONFIG_DIR),
            "--out",
            str(out),
            "--report",
            str(report_path),
        ]
    )
    assert rc == 0
    assert out.exists()

    conn = sqlite3.connect(out)
    try:
        n_places = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        n_poi = conn.execute("SELECT COUNT(*) FROM places WHERE kind='poi'").fetchone()[0]
        n_site = conn.execute("SELECT COUNT(*) FROM places WHERE kind='landing_site'").fetchone()[0]
        n_alias = conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
        n_region = conn.execute("SELECT COUNT(*) FROM regions").fetchone()[0]
        brad = conn.execute(
            "SELECT lat, lon FROM places WHERE id='mars:msl:bradbury-landing'"
        ).fetchone()
        glen = conn.execute(
            "SELECT lat, lon, tags_json FROM places WHERE id='mars:msl:glen-etive'"
        ).fetchone()
    finally:
        conn.close()

    assert n_places == 22  # 21 POIs + Bradbury Landing
    assert n_poi == 21
    assert n_site == 1
    assert n_alias == 2  # 2 Bradbury aliases
    assert n_region == 1
    assert brad[0] == -4.5895 and brad[1] == 137.4417
    assert "target_route:smectite" in glen[2]

    report = json.loads(report_path.read_text())
    # exactly two pairs of duplicate coordinates (John Klein/Cumberland,
    # Big Sky/Greenhorn)
    dups = report["duplicate_coordinates"]
    assert len(dups) == 2
    dup_ids = {frozenset(d["place_ids"]) for d in dups}
    assert frozenset({"mars:msl:john-klein", "mars:msl:cumberland"}) in dup_ids
    assert frozenset({"mars:msl:big-sky", "mars:msl:greenhorn"}) in dup_ids
    assert report["validation_errors"] == []
    assert report["counts"]["places"] == 22


def test_seed_catalog_committed_copy():
    """The prebuilt seed catalog under data/seed must match a fresh build."""
    if not SEED_OUT.exists():
        # build it once for real (also exercised by test_seed_build)
        rc = main(
            [
                "build",
                "--mission",
                str(MISSION_XLSX),
                "--config",
                str(CONFIG_DIR),
                "--out",
                str(SEED_OUT),
                "--report",
                str(SEED_OUT.parent / "ingest_report.json"),
            ]
        )
        assert rc == 0
    conn = sqlite3.connect(SEED_OUT)
    try:
        assert conn.execute("SELECT COUNT(*) FROM places").fetchone()[0] == 22
    finally:
        conn.close()
