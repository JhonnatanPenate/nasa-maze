"""Use case: text search (GET /v1/places/search)."""

from __future__ import annotations

from dataclasses import dataclass

from location_service.domain.ranking import ScoredPlace
from location_service.ports import CatalogIndex


@dataclass(frozen=True)
class SearchOutcome:
    normalized_query: str
    scored: tuple[ScoredPlace, ...]
    total: int


def search_places(
    catalog: CatalogIndex,
    query: str,
    *,
    limit: int = 10,
    kind: str | None = None,
    feature_type: str | None = None,
    source: str | None = None,
    near: tuple[float, float] | None = None,
    region: str | None = None,
) -> SearchOutcome:
    normalized, scored, total = catalog.search(
        query,
        limit=limit,
        kind=kind,
        feature_type=feature_type,
        source=source,
        near=near,
        region=region,
    )
    return SearchOutcome(normalized_query=normalized, scored=tuple(scored), total=total)
