"""Use case: filtered paginated listing (GET /v1/places)."""

from __future__ import annotations

from dataclasses import dataclass

from location_service.domain.geo import BboxTuple, normalize_lon
from location_service.domain.models import Place
from location_service.ports import CatalogIndex


@dataclass(frozen=True)
class ListOutcome:
    total: int
    places: tuple[Place, ...]


def _in_bbox(place: Place, bbox: BboxTuple) -> bool:
    west, south, east, north = bbox
    lat, lon = place.center.lat, place.center.lon
    if not south <= lat <= north:
        return False
    lon_n = normalize_lon(lon)
    if west <= east:
        return west <= lon_n <= east
    return lon_n >= west or lon_n <= east


def list_places(
    catalog: CatalogIndex,
    *,
    kind: str | None = None,
    feature_type: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    region: str | None = None,
    bbox: BboxTuple | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ListOutcome:
    places = catalog.filter_places(
        kind=kind, feature_type=feature_type, source=source, tag=tag, region=region
    )
    if bbox is not None:
        places = [p for p in places if _in_bbox(p, bbox)]
    places = sorted(places, key=lambda p: (p.name_norm or p.name.casefold(), p.id))
    return ListOutcome(total=len(places), places=tuple(places[offset : offset + limit]))
