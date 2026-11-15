"""In-memory catalog index (adapter).

The whole catalog is loaded at startup (a few thousand names at most) and all
searches run in memory - no FTS/R-tree needed (design decision 1).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from location_service.adapters.sqlite_catalog import CatalogData
from location_service.domain.geo import haversine_m
from location_service.domain.models import Place, Region
from location_service.domain.ranking import (
    RankablePlace,
    ScoredPlace,
    build_descriptor_map,
    rank_query,
)
from location_service.domain.text import normalize_text


class MemoryIndex:
    def __init__(self, data: CatalogData, *, fuzzy_min_ratio: float = 60.0) -> None:
        self._data = data
        self._places: dict[str, Place] = {p.id: p for p in data.places}
        self._alias_norms: dict[str, tuple[str, ...]] = {
            p.id: tuple(dict.fromkeys(n for n in (normalize_text(a) for a in p.aliases) if n))
            for p in data.places
        }
        self._fuzzy_min_ratio = fuzzy_min_ratio
        self._descriptor_map = build_descriptor_map(
            [p.feature_type for p in data.places],
            {},  # translations injected via with_descriptor_translations
        )
        self._regions_with_bbox = [r for r in data.regions if r.bbox is not None]

    # -- construction helpers -------------------------------------------------

    @classmethod
    def from_data(
        cls,
        data: CatalogData,
        *,
        fuzzy_min_ratio: float = 60.0,
        type_word_translations: Mapping[str, str] | None = None,
    ) -> MemoryIndex:
        idx = cls(data, fuzzy_min_ratio=fuzzy_min_ratio)
        idx._descriptor_map = build_descriptor_map(
            [p.feature_type for p in data.places],
            type_word_translations or {},
        )
        return idx

    # -- CatalogRepository ----------------------------------------------------

    def places(self) -> Sequence[Place]:
        return self._data.places

    def get(self, place_id: str) -> Place | None:
        return self._places.get(place_id)

    def regions(self) -> Sequence[Region]:
        return self._data.regions

    def meta(self) -> Mapping[str, str]:
        return self._data.meta

    def feature_type_counts(self) -> Mapping[str, int]:
        return Counter(p.feature_type for p in self._data.places)

    # -- derived context ------------------------------------------------------

    def regions_containing(self, lat: float, lon: float) -> list[str]:
        return [r.id for r in self._regions_with_bbox if r.bbox and r.bbox.contains(lat, lon)]

    def in_any_region(self, place: Place) -> bool:
        return bool(self.regions_containing(place.center.lat, place.center.lon))

    def _rankable(self, place: Place, near: tuple[float, float] | None) -> RankablePlace:
        dist = None
        if near is not None:
            dist = haversine_m(place.center.lat, place.center.lon, near[0], near[1])
        return RankablePlace(
            place=place,
            alias_norms=self._alias_norms.get(place.id, ()),
            in_aoi=self.in_any_region(place),
            dist_to_near_m=dist,
        )

    def filter_places(
        self,
        *,
        kind: str | None = None,
        feature_type: str | None = None,
        source: str | None = None,
        tag: str | None = None,
        region: str | None = None,
    ) -> list[Place]:
        region_bbox = None
        if region is not None:
            reg = next((r for r in self._data.regions if r.id == region), None)
            region_bbox = reg.bbox if reg else None
            if region_bbox is None:
                return []
        out = []
        for p in self._data.places:
            if kind is not None and p.kind != kind:
                continue
            if feature_type is not None and p.feature_type != feature_type:
                continue
            if source is not None and p.source != source:
                continue
            if tag is not None and tag not in p.tags:
                continue
            if region_bbox is not None and not region_bbox.contains(p.center.lat, p.center.lon):
                continue
            out.append(p)
        return out

    # -- use-case support -----------------------------------------------------

    def rank(self, query: str, *, near: tuple[float, float] | None = None) -> list[ScoredPlace]:
        """Score ALL places for a query (no filters, no limit)."""
        items = [self._rankable(p, near) for p in self._data.places]
        return rank_query(
            query,
            items,
            descriptor_map=self._descriptor_map,
            fuzzy_min_ratio=self._fuzzy_min_ratio,
        )

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
    ) -> tuple[str, list[ScoredPlace], int]:
        from location_service.domain.text import normalize_text

        candidates = self.filter_places(
            kind=kind, feature_type=feature_type, source=source, region=region
        )
        items = [self._rankable(p, near) for p in candidates]
        scored = rank_query(
            query,
            items,
            descriptor_map=self._descriptor_map,
            fuzzy_min_ratio=self._fuzzy_min_ratio,
        )
        return normalize_text(query), scored[:limit], len(scored)

    def distances(
        self, lat: float, lon: float, places: Sequence[Place] | None = None
    ) -> list[tuple[float, Place]]:
        target = places if places is not None else self._data.places
        return sorted(
            ((haversine_m(lat, lon, p.center.lat, p.center.lon), p) for p in target),
            key=lambda t: (t[0], t[1].id),
        )

    def nearest_within(
        self, lat: float, lon: float, radius_m: float, *, exclude_id: str | None = None
    ) -> list[tuple[float, Place]]:
        return [(d, p) for d, p in self.distances(lat, lon) if d <= radius_m and p.id != exclude_id]

    def co_located(
        self, lat: float, lon: float, *, exclude_id: str | None = None, within_m: float = 10.0
    ) -> list[Place]:
        return [p for d, p in self.nearest_within(lat, lon, within_m, exclude_id=exclude_id)]
