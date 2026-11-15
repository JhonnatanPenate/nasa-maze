"""Offline catalog build CLI (README section 3.5).

    python -m location_service.ingest build \
        --gazetteer data/raw/mars/gazetteer/<file> \
        --mission   data/gale/processed/gale_puntos_quimica.xlsx \
        --config    location-service/config \
        --out       data/processed/mars/location/location_catalog.sqlite

Seed mode: omit --gazetteer to build a catalog with only mission POIs +
landing sites + regions (useful for development and minimal offline demo).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from location_service.domain.models import Place
from location_service.ingest.config_loader import apply_aliases, load_config_dir
from location_service.ingest.gazetteer import read_gazetteer
from location_service.ingest.mission_points import IngestError, read_mission_points
from location_service.ingest.validate import schema_version, validate_catalog
from location_service.ingest.writer import write_catalog

_DEFAULT_OUT_GAZETTEER = Path("data/processed/mars/location/location_catalog.sqlite")
_DEFAULT_OUT_SEED = Path("data/seed/location_catalog_seed.sqlite")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_record(path: Path, count: int) -> dict[str, Any]:
    return {"path": str(path), "sha256": _sha256(path), "records": count}


def _name_collisions(places: list[Place]) -> list[dict[str, Any]]:
    by_norm: dict[str, list[str]] = {}
    for p in places:
        by_norm.setdefault(p.name_norm, []).append(p.id)
    return [{"name_norm": norm, "place_ids": ids} for norm, ids in by_norm.items() if len(ids) > 1]


def _duplicate_coordinates(places: list[Place]) -> list[dict[str, Any]]:
    by_point: dict[tuple[float, float], list[str]] = {}
    for p in places:
        key = (round(p.center.lat, 6), round(p.center.lon, 6))
        by_point.setdefault(key, []).append(p.id)
    return [
        {"lat": lat, "lon": lon, "place_ids": ids}
        for (lat, lon), ids in by_point.items()
        if len(ids) > 1
    ]


def build_catalog(args: argparse.Namespace) -> int:
    config_dir = Path(args.config)
    if not config_dir.is_dir():
        print(f"error: config dir not found: {config_dir}", file=sys.stderr)
        return 2
    config = load_config_dir(config_dir)

    out = (
        Path(args.out)
        if args.out
        else (_DEFAULT_OUT_GAZETTEER if args.gazetteer else _DEFAULT_OUT_SEED)
    )
    report_path = Path(args.report) if args.report else out.parent / "ingest_report.json"

    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "out": str(out),
        "report": str(report_path),
        "discarded": [],
        "warnings": [],
        "id_collisions": [],
        "sources": {},
    }

    places: list[Place] = []
    seen_ids: set[str] = set()
    lon_convention = None

    if args.gazetteer:
        gaz_path = Path(args.gazetteer)
        gaz_places, lon_convention = read_gazetteer(gaz_path, config.gazetteer, report, seen_ids)
        places.extend(gaz_places)
        report["sources"]["iau_gazetteer"] = _source_record(gaz_path, len(gaz_places))
    else:
        report["warnings"].append(
            "seed mode: no Gazetteer file; catalog contains mission data only"
        )

    if args.mission:
        mission_path = Path(args.mission)
        mission_places = read_mission_points(mission_path, config.mission, report, seen_ids)
        places.extend(mission_places)
        report["sources"]["mission_msl"] = _source_record(mission_path, len(mission_places))
    else:
        report["warnings"].append("no --mission file; only config places built")

    aliases_map = apply_aliases(places, config.aliases, report)
    regions = config.regions

    built_at = datetime.now(UTC)
    catalog_version = f"{built_at:%Y-%m-%d}.{built_at:%H%M%S}"
    counts = {
        "places": len(places),
        "aliases": sum(len(v) for v in aliases_map.values()),
        "regions": len(regions),
        "by_source": dict(Counter(p.source for p in places)),
        "by_kind": dict(Counter(p.kind for p in places)),
        "by_feature_type": dict(Counter(p.feature_type for p in places)),
    }

    meta = {
        "schema_version": str(schema_version()),
        "built_at": built_at.isoformat(),
        "catalog_version": catalog_version,
        "coordinate_body": "mars",
        "coordinate_crs": "IAU_2015:49900",
        "coordinate_lat_type": "planetocentric",
        "coordinate_lon_convention": "east_positive_0_360",
        "coordinate_radius_m": "3396190",
        "counts": json.dumps(counts, sort_keys=True),
        "convention_lon": lon_convention or "n/a (seed mode)",
        "convention_lat": "planetocentric",
    }
    for label, rec in report["sources"].items():
        meta[f"source_{label}_sha256"] = rec["sha256"]
        meta[f"source_{label}_records"] = str(rec["records"])

    errors = validate_catalog(places, regions, report)
    report["validation_errors"] = errors
    report["counts"] = counts
    report["catalog_version"] = catalog_version
    report["aliases_applied"] = {k: list(v) for k, v in aliases_map.items()}
    report["name_collisions"] = _name_collisions(places)
    report["duplicate_coordinates"] = _duplicate_coordinates(places)
    report["finished_at"] = datetime.now(UTC).isoformat()

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str) + "\n")

    if errors:
        print("catalog validation FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"report written to {report_path}", file=sys.stderr)
        return 1

    write_catalog(out, places, aliases_map, regions, meta)
    print(f"catalog written: {out} ({len(places)} places, version {catalog_version})")
    print(f"report written:  {report_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="location-ingest")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build location_catalog.sqlite")
    build.add_argument("--gazetteer", help="Gazetteer file (.csv/.tsv/.geojson/.shp)")
    build.add_argument("--mission", help="MSL targets .xlsx")
    build.add_argument("--config", default="config", help="curated YAML dir")
    build.add_argument("--out", help="output sqlite path")
    build.add_argument("--report", help="ingest_report.json path")
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            return build_catalog(args)
    except IngestError as exc:
        print(f"ingest error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
