"""Shared fixtures: build the seed catalog once, expose a TestClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from location_service.ingest.__main__ import main as ingest_main
from location_service.main import create_app
from location_service.settings import Settings

SERVICE_ROOT = Path(__file__).parent.parent
REPO_ROOT = SERVICE_ROOT.parent
MISSION_XLSX = REPO_ROOT / "data/gale/processed/gale_puntos_quimica.xlsx"
CONFIG_DIR = SERVICE_ROOT / "config"


@pytest.fixture(scope="session")
def catalog_path(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("catalog") / "location_catalog.sqlite"
    report = out.parent / "ingest_report.json"
    rc = ingest_main(
        [
            "build",
            "--mission",
            str(MISSION_XLSX),
            "--config",
            str(CONFIG_DIR),
            "--out",
            str(out),
            "--report",
            str(report),
        ]
    )
    assert rc == 0, "seed catalog build failed"
    return out


@pytest.fixture()
def client(catalog_path) -> TestClient:
    settings = Settings(
        catalog_path=catalog_path,
        config_dir=CONFIG_DIR,
        catalog_required=True,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def no_catalog_client() -> TestClient:
    settings = Settings(
        catalog_path=Path("/nonexistent/catalog.sqlite"),
        seed_catalog_path=Path("/nonexistent/seed.sqlite"),
        catalog_required=False,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
