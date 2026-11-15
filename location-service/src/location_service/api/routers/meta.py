"""GET /v1/meta/* and POST /v1/admin/reload."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Request

from location_service.adapters.memory_index import MemoryIndex
from location_service.adapters.sqlite_catalog import load_catalog
from location_service.api.deps import get_catalog
from location_service.api.schemas import (
    CatalogMetaResponse,
    FeatureTypeCount,
    FeatureTypesResponse,
    ReloadResponse,
    coordinate_system_out,
)
from location_service.errors import InvalidParameterError
from location_service.ports import CatalogIndex
from location_service.settings import Settings

router = APIRouter(tags=["meta"])


def _catalog_version(catalog: CatalogIndex) -> str:
    return catalog.meta().get("catalog_version", "unknown")


def _type_translations(config_dir: Path) -> dict[str, str]:
    path = Path(config_dir) / "gazetteer_columns.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {str(k): str(v) for k, v in (data.get("type_word_translations") or {}).items()}
    except Exception:
        return {}


@router.get("/v1/meta/catalog")
def catalog_meta(catalog: CatalogIndex = Depends(get_catalog)) -> CatalogMetaResponse:
    meta = catalog.meta()
    sources = {
        key[len("source_") : -len("_sha256")]: value
        for key, value in meta.items()
        if key.startswith("source_") and key.endswith("_sha256")
    }
    try:
        counts = json.loads(meta.get("counts", "{}"))
    except json.JSONDecodeError:
        counts = {}
    return CatalogMetaResponse(
        catalog_version=_catalog_version(catalog),
        built_at=meta.get("built_at", ""),
        schema_version=int(meta.get("schema_version", "0") or 0),
        sources=sources,
        counts=counts,
        coordinate_system=coordinate_system_out(),
    )


@router.get("/v1/meta/feature-types")
def feature_types(catalog: CatalogIndex = Depends(get_catalog)) -> FeatureTypesResponse:
    counts = catalog.feature_type_counts()
    return FeatureTypesResponse(
        feature_types=[
            FeatureTypeCount(feature_type=ft, count=n)
            for ft, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
    )


@router.post("/v1/admin/reload")
def reload_catalog(request: Request) -> ReloadResponse:
    settings: Settings = request.app.state.settings
    if not settings.admin_enabled:
        raise InvalidParameterError(
            "admin reload is disabled (LOCATION_ADMIN_ENABLED=false)"
        )
    path = Path(settings.catalog_path)
    if not path.exists():
        path = Path(settings.seed_catalog_path)
    data = load_catalog(path)
    request.app.state.index = MemoryIndex.from_data(
        data,
        fuzzy_min_ratio=settings.fuzzy_min_score * 100.0,
        type_word_translations=_type_translations(settings.config_dir),
    )
    return ReloadResponse(
        status="reloaded", catalog_version=data.meta.get("catalog_version", "unknown")
    )
