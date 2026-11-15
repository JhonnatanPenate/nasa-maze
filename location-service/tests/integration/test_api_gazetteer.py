"""Golden cases 7-8: require the real USGS Gazetteer.

Skipped unless a gazetteer file exists in ``data/raw/mars/gazetteer/``
(repo root). When present, a full catalog (mission + gazetteer) is built
once per module and the API is exercised through TestClient.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from location_service.ingest.__main__ import main as ingest_main
from location_service.main import create_app
from location_service.settings import Settings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
GAZETTEER_DIR = REPO_ROOT / "data" / "raw" / "mars" / "gazetteer"
MISSION_XLSX = REPO_ROOT / "data" / "gale" / "processed" / "gale_puntos_quimica.xlsx"
CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

_GAZETTEER_FILES = (
    sorted(
        p
        for p in GAZETTEER_DIR.glob("*")
        if p.is_file() and p.suffix.lower() in {".csv", ".tsv", ".json", ".geojson", ".shp"}
    )
    if GAZETTEER_DIR.is_dir()
    else []
)

pytestmark = pytest.mark.skipif(
    not _GAZETTEER_FILES,
    reason="requires Gazetteer: no file in data/raw/mars/gazetteer/",
)


@pytest.fixture(scope="module")
def gazetteer_client(tmp_path_factory):
    out = tmp_path_factory.mktemp("gazetteer-catalog") / "location_catalog.sqlite"
    report = out.parent / "ingest_report.json"
    rc = ingest_main(
        [
            "build",
            "--gazetteer",
            str(_GAZETTEER_FILES[0]),
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
    assert rc == 0, "gazetteer catalog build failed"
    settings = Settings(catalog_path=out, config_dir=CONFIG_DIR)
    with TestClient(create_app(settings)) as client:
        yield client


class TestGazetteerGolden:
    def test_case7_mount_sharp(self, gazetteer_client):
        r = gazetteer_client.get("/v1/places/search", params={"q": "Mount Sharp"})
        assert r.status_code == 200
        results = r.json()["results"]
        assert results, "Mount Sharp should resolve via alias to Aeolis Mons"
        top = results[0]["place"]
        assert top["name"].lower() in {"aeolis mons", "mount sharp"}

    @pytest.mark.parametrize("query", ["Gale crater", "cráter Gale"])
    def test_case8_gale_crater(self, gazetteer_client, query):
        r = gazetteer_client.get("/v1/places/search", params={"q": query})
        assert r.status_code == 200
        results = r.json()["results"]
        assert results
        top = results[0]["place"]
        assert "gale" in top["name"].lower()
        assert top["feature_type"] == "crater"
        assert top["center"]["lat"] == pytest.approx(-5.4, abs=0.5)
        assert top["center"]["lon"] == pytest.approx(137.8, abs=0.5)
