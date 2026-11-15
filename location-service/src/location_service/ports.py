"""Repository ports (hexagonal boundary). Implemented by adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from location_service.domain.models import Place, Region
from location_service.domain.ranking import ScoredPlace


class CatalogRepository(Protocol):
    """Read-only access to the loaded catalog."""

    def places(self) -> Sequence[Place]: ...

    def get(self, place_id: str) -> Place | None: ...

    def regions(self) -> Sequence[Region]: ...

    def meta(self) -> Mapping[str, str]: ...

    def feature_type_counts(self) -> Mapping[str, int]: ...


class CatalogIndex(CatalogRepository, Protocol):
    """In-memory index capabilities used by the application layer."""

    def filter_places(
        self,
        *,
        kind: str | None = None,
        feature_type: str | None = None,
        source: str | None = None,
        tag: str | None = None,
        region: str | None = None,
    ) -> list[Place]: ...

    def rank(
        self, query: str, *, near: tuple[float, float] | None = None
    ) -> list[ScoredPlace]: ...

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        kind: str | None = None,
        feature_type: str | None = None,
        source: str | None = None,
        near: tuple[float, float] | None = None,
        region: str | None = None,
    ) -> tuple[str, list[ScoredPlace], int]: ...

    def distances(
        self, lat: float, lon: float, places: Sequence[Place] | None = None
    ) -> list[tuple[float, Place]]: ...

    def nearest_within(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        *,
        exclude_id: str | None = None,
    ) -> list[tuple[float, Place]]: ...

    def co_located(
        self,
        lat: float,
        lon: float,
        *,
        exclude_id: str | None = None,
        within_m: float = 10.0,
    ) -> list[Place]: ...

    def regions_containing(self, lat: float, lon: float) -> list[str]: ...

    def in_any_region(self, place: Place) -> bool: ...
