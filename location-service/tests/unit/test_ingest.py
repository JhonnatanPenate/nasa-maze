"""Unit tests for the ingestion pipeline (Phase 2)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from location_service.ingest.config_loader import (
    load_gazetteer_config,
    load_mission_config,
)
from location_service.ingest.gazetteer import (
    IngestError,
    detect_lon_convention,
    read_gazetteer,
    to_east_lon,
)
from location_service.ingest.mission_points import read_mission_points
from location_service.ingest.writer import write_catalog

FIXTURES = Path(__file__).parent.parent / "fixtures"
SERVICE_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = SERVICE_ROOT / "config"


def _report() -> dict:
    return {"discarded": [], "warnings": [], "id_collisions": []}


class TestMissionPoints:
    def test_mini_mission(self, tmp_path):
        config = load_mission_config(CONFIG_DIR / "mission_points.yaml")
        seen: set[str] = set()
        places = read_mission_points(FIXTURES / "mini-mission.xlsx", config, _report(), seen)
        # 3 spreadsheet rows + 1 landing site
        assert len(places) == 4
        by_id = {p.id: p for p in places}
        alpha = by_id["mars:msl:test-alpha"]
        assert alpha.kind == "poi"
        assert alpha.feature_type == "mission_target"
        assert alpha.source == "mission_msl"
        assert alpha.center.lat == pytest.approx(-4.60)
        assert alpha.center.lon == pytest.approx(137.40)
        assert alpha.elevation_m == pytest.approx(-4500)
        # sol and non-null percentages land in properties; all-null column dropped
        assert alpha.properties["sol"] == 10
        assert alpha.properties["hematita_pct"] == 12.5
        assert "col_all_null" not in alpha.properties
        assert "esmectitas_pct" not in alpha.properties  # NaN for this row
        assert "elevacion_m" not in alpha.properties
        brad = by_id["mars:msl:bradbury-landing"]
        assert brad.kind == "landing_site"
        assert brad.feature_type == "landing_site"
        assert brad.center.lon == pytest.approx(137.4417)


class TestGazetteerMini:
    @pytest.fixture
    def gaz_config(self):
        return load_gazetteer_config(FIXTURES / "mini-gazetteer-columns.yaml")

    def test_reads_and_converts(self, gaz_config):
        report = _report()
        seen: set[str] = set()
        places, convention = read_gazetteer(
            FIXTURES / "mini-gazetteer.csv", gaz_config, report, seen
        )
        assert convention == "signed_180_180"
        by_name = {p.name: p for p in places}
        # signed -180..180 normalized to [0,360)
        assert by_name["Olympus Mons"].center.lat == pytest.approx(18.65)
        assert by_name["Olympus Mons"].center.lon == pytest.approx(226.2)
        assert by_name["Another Crater"].center.lon == pytest.approx(250.0)
        # west-positive column converted: (360 - w) % 360
        assert by_name["West Feature Alpha"].center.lon == pytest.approx(327.2)
        assert by_name["West Feature Beta"].center.lon == pytest.approx(160.0)
        assert by_name["West Feature Gamma"].center.lon == pytest.approx(0.0)
        # kinds / sources / ids
        olympus = by_name["Olympus Mons"]
        assert olympus.kind == "feature"
        assert olympus.source == "iau_gazetteer"
        assert olympus.id == "mars:iau:10452"
        assert olympus.feature_type == "mons"
        assert olympus.diameter_km == pytest.approx(624.0)
        assert olympus.approval_status == "Approved"
        assert olympus.bbox is not None and olympus.bbox.west == pytest.approx(226.0)
        # 18 rows - 5 discarded = 13 places
        assert len(places) == 13
        assert len(report["discarded"]) == 5

    def test_east_positive_detection(self, gaz_config, tmp_path):
        # copy east fixture with same columns mapping
        report = _report()
        seen: set[str] = set()
        places, convention = read_gazetteer(
            FIXTURES / "mini-gazetteer-east.csv", gaz_config, report, seen
        )
        assert convention == "east_0_360"
        by_name = {p.name: p for p in places}
        assert by_name["East Positive Mons"].center.lon == pytest.approx(250.5)
        assert by_name["East Positive Crater"].center.lon == pytest.approx(300.25)

    def test_ambiguous_convention_aborts(self, gaz_config, tmp_path):
        csv = tmp_path / "amb.csv"
        csv.write_text(
            "feature_id,feature_name,descriptor,body,center_lat,center_lon,"
            "center_lon_west,bbox_west,bbox_south,bbox_east,bbox_north,"
            "diameter_km,approval_status,name_origin\n"
            "1,Foo,crater,Mars,1.0,10.0,,,,,,,Approved,x\n"
            "2,Bar,crater,Mars,2.0,170.0,,,,,,,Approved,x\n"
        )
        with pytest.raises(IngestError, match="convention"):
            read_gazetteer(csv, gaz_config, _report(), set())

    def test_west_positive_declared(self, gaz_config, tmp_path):
        import yaml

        cfg_path = tmp_path / "cols.yaml"
        data = yaml.safe_load((FIXTURES / "mini-gazetteer-columns.yaml").read_text())
        data["convention"]["lon"] = "west_positive"
        cfg_path.write_text(yaml.safe_dump(data))
        cfg = load_gazetteer_config(cfg_path)
        report = _report()
        places, convention = read_gazetteer(
            FIXTURES / "mini-gazetteer.csv", cfg, report, set()
        )
        assert convention == "west_positive"
        by_name = {p.name: p for p in places}
        # Olympus lon -133.8 west-positive -> (360 - (-133.8)) % 360 = 133.8 east
        assert by_name["Olympus Mons"].center.lon == pytest.approx(133.8)


class TestDetectLonConvention:
    def test_signed(self):
        assert detect_lon_convention([-10.0, 45.0, 170.0], "auto") == "signed_180_180"

    def test_east(self):
        assert detect_lon_convention([10.0, 200.0, 350.0], "auto") == "east_0_360"

    def test_declared_wins(self):
        assert detect_lon_convention([10.0], "west_positive") == "west_positive"

    def test_mixed_aborts(self):
        with pytest.raises(IngestError):
            detect_lon_convention([-10.0, 250.0], "auto")

    def test_ambiguous_aborts(self):
        with pytest.raises(IngestError):
            detect_lon_convention([10.0, 45.0], "auto")

    def test_to_east(self):
        assert to_east_lon(-133.8, "signed_180_180") == pytest.approx(226.2)
        assert to_east_lon(32.8, "west_positive") == pytest.approx(327.2)
        assert to_east_lon(0.0, "west_positive") == pytest.approx(0.0)


class TestWriter:
    def test_roundtrip(self, tmp_path):
        from location_service.domain.models import Bbox, Coordinate, Place

        places = [
            Place(
                id="mars:msl:x",
                name="X",
                body="mars",
                kind="poi",
                feature_type="mission_target",
                source="mission_msl",
                center=Coordinate(lat=-4.5, lon=137.4),
                name_norm="x",
                tags=("t1",),
                properties={"sol": 1},
                bbox=Bbox(1.0, -5.0, 2.0, -4.0),
            )
        ]
        out = tmp_path / "cat.sqlite"
        write_catalog(out, places, {"mars:msl:x": ("Alias X",)}, (), {"k": "v"})
        conn = sqlite3.connect(out)
        try:
            row = conn.execute("SELECT id, lat, lon, tags_json FROM places").fetchone()
            assert row[0] == "mars:msl:x"
            assert row[1] == pytest.approx(-4.5)
            assert json.loads(row[3]) == ["t1"]
            assert conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0] == 1
            assert conn.execute("SELECT value FROM catalog_meta WHERE key='k'").fetchone()[0] == "v"
        finally:
            conn.close()
