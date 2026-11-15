"""Load curated YAML configuration (layer C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from location_service.domain.models import Bbox, Place, Region
from location_service.domain.text import normalize_text


@dataclass(frozen=True)
class GazetteerConfig:
    columns: dict[str, str]
    convention_lon: str = "auto"  # auto | east_0_360 | signed_180_180 | west_positive
    convention_lat: str = "planetocentric"
    approval_filter: str = "approved"  # approved | all
    # raw approval-column values that count as "approved" (case-insensitive);
    # e.g. the USGS shapefile uses "Adopted by IAU" instead of "Approved"
    approved_values: tuple[str, ...] = ("approved",)
    type_word_translations: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MissionConfig:
    landing_sites: tuple[dict[str, Any], ...] = ()
    tags: dict[str, tuple[str, ...]] = field(default_factory=dict)  # tag -> names


@dataclass(frozen=True)
class AliasesConfig:
    by_id: dict[str, tuple[str, ...]] = field(default_factory=dict)
    by_name: dict[str, tuple[str, ...]] = field(default_factory=dict)  # norm name -> aliases


@dataclass(frozen=True)
class ServiceConfig:
    gazetteer: GazetteerConfig
    mission: MissionConfig
    regions: tuple[Region, ...]
    aliases: AliasesConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def load_gazetteer_config(path: Path) -> GazetteerConfig:
    data = _load_yaml(path)
    conv = data.get("convention") or {}
    filters = data.get("filters") or {}
    translations = {str(k): str(v) for k, v in (data.get("type_word_translations") or {}).items()}
    return GazetteerConfig(
        columns={str(k): str(v) for k, v in (data.get("columns") or {}).items()},
        convention_lon=str(conv.get("lon", "auto")),
        convention_lat=str(conv.get("lat", "planetocentric")),
        approval_filter=str(filters.get("approval", "approved")),
        approved_values=tuple(
            str(v).strip().lower()
            for v in (filters.get("approved_values") or ("approved",))
        ),
        type_word_translations=translations,
    )


def load_mission_config(path: Path) -> MissionConfig:
    data = _load_yaml(path)
    landing = tuple(data.get("landing_sites") or ())
    tags = {
        str(tag): tuple(str(n) for n in names) for tag, names in (data.get("tags") or {}).items()
    }
    return MissionConfig(landing_sites=landing, tags=tags)


def load_regions_config(path: Path) -> tuple[Region, ...]:
    data = _load_yaml(path)
    regions = []
    for r in data.get("regions") or ():
        bbox = r.get("bbox")
        regions.append(
            Region(
                id=str(r["id"]),
                name=str(r.get("name", r["id"])),
                kind=str(r.get("kind", "aoi")),
                source=str(r.get("source", "config")),
                bbox=(
                    Bbox(
                        west=float(bbox["west"]),
                        south=float(bbox["south"]),
                        east=float(bbox["east"]),
                        north=float(bbox["north"]),
                    )
                    if bbox
                    else None
                ),
                note=r.get("note"),
            )
        )
    return tuple(regions)


def load_aliases_config(path: Path) -> AliasesConfig:
    data = _load_yaml(path)
    by_id: dict[str, tuple[str, ...]] = {}
    by_name: dict[str, tuple[str, ...]] = {}
    for key, aliases in (data.get("aliases") or {}).items():
        key = str(key)
        values = tuple(str(a) for a in (aliases or ()))
        if key.startswith("name:"):
            by_name[normalize_text(key[5:])] = values
        else:
            by_id[key] = values
    return AliasesConfig(by_id=by_id, by_name=by_name)


def load_config_dir(config_dir: Path) -> ServiceConfig:
    """Load all curated YAML files from a config directory."""
    config_dir = Path(config_dir)
    return ServiceConfig(
        gazetteer=load_gazetteer_config(config_dir / "gazetteer_columns.yaml"),
        mission=load_mission_config(config_dir / "mission_points.yaml"),
        regions=load_regions_config(config_dir / "regions.yaml"),
        aliases=load_aliases_config(config_dir / "aliases.yaml"),
    )


def apply_aliases(
    places: list[Place],
    aliases: AliasesConfig,
    report: dict[str, Any],
) -> dict[str, tuple[str, ...]]:
    """Resolve configured aliases to place ids.

    Returns {place_id: (raw aliases,)} for places that received aliases.
    """
    result: dict[str, tuple[str, ...]] = {}
    by_norm: dict[str, list[str]] = {}
    for p in places:
        by_norm.setdefault(p.name_norm or normalize_text(p.name), []).append(p.id)

    for pid, values in aliases.by_id.items():
        if any(p.id == pid for p in places):
            result[pid] = values
        else:
            report.setdefault("warnings", []).append(f"alias target id not found: {pid}")

    for norm_name, values in aliases.by_name.items():
        ids = by_norm.get(norm_name, [])
        if not ids:
            report.setdefault("warnings", []).append(f"alias target name not found: {norm_name}")
            continue
        for pid in ids:
            result[pid] = tuple(dict.fromkeys((*result.get(pid, ()), *values)))
    return result
