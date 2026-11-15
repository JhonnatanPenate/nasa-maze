"""Use case: reverse geocoding (GET /v1/places/reverse)."""

from __future__ import annotations

from dataclasses import dataclass

from location_service.domain.geo import haversine_m
from location_service.domain.models import Place
from location_service.ports import CatalogIndex


@dataclass(frozen=True)
class ReverseOutcome:
    nearest: tuple[tuple[float, Place], ...]
    containing: tuple[Place, ...]
    regions: tuple[str, ...]


def reverse_lookup(
    catalog: CatalogIndex,
    lat: float,
    lon: float,
    *,
    radius_m: float = 5000.0,
    limit: int = 5,
    kind: str | None = None,
) -> ReverseOutcome:
    places = [p for p in catalog.places() if kind is None or p.kind == kind]
    dist_pairs = catalog.distances(lat, lon, places)
    nearest = tuple((d, p) for d, p in dist_pairs if d <= radius_m)[:limit]

    containing = tuple(
        p
        for p in places
        if p.diameter_km is not None
        and haversine_m(lat, lon, p.center.lat, p.center.lon) <= p.diameter_km * 500.0
    )
    regions = tuple(catalog.regions_containing(lat, lon))
    return ReverseOutcome(nearest=nearest, containing=containing, regions=regions)
