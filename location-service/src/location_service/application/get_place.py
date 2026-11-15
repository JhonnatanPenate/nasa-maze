"""Use case: place by id (GET /v1/places/{place_id})."""

from __future__ import annotations

from location_service.domain.models import Place
from location_service.ports import CatalogRepository


def get_place(catalog: CatalogRepository, place_id: str) -> Place | None:
    return catalog.get(place_id)
