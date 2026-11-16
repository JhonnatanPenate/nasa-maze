"""Load ``config/environment_columns.yaml`` for the ingest pipeline.

The YAML maps each workbook's source columns to canonical names, units and
optional conversions (plan §5/§8). Loaded once per CLI run; invalid config
fails fast before any workbook is touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ColumnSpec:
    """One source column -> canonical field mapping."""

    canonical: str
    unit: str | None = None
    conversion: str | None = None


@dataclass(frozen=True)
class WorkbookConfig:
    """Column mapping for one environmental workbook."""

    name: str  # "rems" | "rad"
    source: str
    sheet: str
    key_columns: dict[str, ColumnSpec] = field(default_factory=dict)
    value_columns: dict[str, ColumnSpec] = field(default_factory=dict)
    unit_column: dict[str, ColumnSpec] = field(default_factory=dict)
    selected_channel: str | None = None


@dataclass(frozen=True)
class EnvironmentColumnsConfig:
    version: int
    rems: WorkbookConfig
    rad: WorkbookConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read config file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Config file {path} must contain a YAML mapping")
    return raw


def _column_specs(raw: Any, where: str) -> dict[str, ColumnSpec]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a mapping of source columns")
    specs: dict[str, ColumnSpec] = {}
    for source_col, spec in raw.items():
        if not isinstance(spec, dict) or "canonical" not in spec:
            raise ValueError(f"{where}.{source_col} must define at least 'canonical'")
        specs[str(source_col)] = ColumnSpec(
            canonical=str(spec["canonical"]),
            unit=spec.get("unit"),
            conversion=spec.get("conversion"),
        )
    return specs


def _workbook_config(name: str, raw: Any) -> WorkbookConfig:
    if not isinstance(raw, dict):
        raise ValueError(f"environment_columns.yaml section '{name}' missing")
    source = raw.get("source")
    sheet = raw.get("sheet")
    if not source or not sheet:
        raise ValueError(f"environment_columns.yaml '{name}' needs source+sheet")
    return WorkbookConfig(
        name=name,
        source=str(source),
        sheet=str(sheet),
        key_columns=_column_specs(raw.get("key_columns"), f"{name}.key_columns"),
        value_columns=_column_specs(raw.get("value_columns"), f"{name}.value_columns"),
        unit_column=_column_specs(raw.get("unit_column"), f"{name}.unit_column"),
        selected_channel=(str(raw["selected_channel"]) if raw.get("selected_channel") else None),
    )


def load_environment_columns(path: str | Path) -> EnvironmentColumnsConfig:
    """Parse ``environment_columns.yaml``; fails fast on bad structure."""
    file_path = Path(path)
    raw = _load_yaml(file_path)
    return EnvironmentColumnsConfig(
        version=int(raw.get("version", 1)),
        rems=_workbook_config("rems", raw.get("rems")),
        rad=_workbook_config("rad", raw.get("rad")),
    )
