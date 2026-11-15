"""Dependency injection for routers."""

from __future__ import annotations

from fastapi import Request

from location_service.domain.models import Place
from location_service.errors import CatalogUnavailableError
from location_service.ports import CatalogIndex


def get_catalog(request: Request) -> CatalogIndex:
    index: CatalogIndex | None = getattr(request.app.state, "index", None)
    if index is None:
        raise CatalogUnavailableError("catalog is not loaded")
    return index


def catalog_version(catalog: CatalogIndex) -> str:
    return catalog.meta().get("catalog_version", "unknown")


def regions_of_place(catalog: CatalogIndex, place: Place) -> list[str]:
    return catalog.regions_containing(place.center.lat, place.center.lon)
