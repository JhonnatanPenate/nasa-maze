"""Place endpoints: search, reverse, list, get-by-id."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query

from location_service.api.deps import catalog_version, get_catalog, regions_of_place
from location_service.api.schemas import (
    Center,
    PlaceListResponse,
    PlaceResponse,
    ReverseContainingItem,
    ReverseNearestItem,
    ReverseResponse,
    SearchResponse,
    SearchResultItem,
    coordinate_system_out,
    place_out,
)
from location_service.application.get_place import get_place
from location_service.application.list_places import list_places
from location_service.application.resolve_endpoints import check_body
from location_service.application.reverse_lookup import reverse_lookup
from location_service.application.search_places import search_places
from location_service.domain.geo import BboxTuple, validate_lat_lon
from location_service.errors import (
    InvalidParameterError,
    NotFoundError,
    OutOfRangeError,
)
from location_service.ports import CatalogIndex

router = APIRouter(tags=["places"])

_KINDS = {"feature", "poi", "landing_site"}
_SOURCES = {"iau_gazetteer", "mission_msl", "config"}


def _check_kind(kind: str | None) -> None:
    if kind is not None and kind not in _KINDS:
        raise InvalidParameterError(f"kind must be one of {sorted(_KINDS)}; got {kind!r}")


def _check_source(source: str | None) -> None:
    if source is not None and source not in _SOURCES:
        raise InvalidParameterError(
            f"source must be one of {sorted(_SOURCES)}; got {source!r}"
        )


def _near(near_lat: float | None, near_lon: float | None) -> tuple[float, float] | None:
    if near_lat is None and near_lon is None:
        return None
    if near_lat is None or near_lon is None:
        raise InvalidParameterError("near_lat and near_lon must be provided together")
    try:
        lat, lon = validate_lat_lon(near_lat, near_lon)
    except ValueError as exc:
        raise OutOfRangeError(str(exc)) from exc
    return (lat, lon)


@router.get("/v1/places/search")
def search(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    kind: str | None = None,
    feature_type: str | None = None,
    source: str | None = None,
    near_lat: float | None = None,
    near_lon: float | None = None,
    region: str | None = None,
    body: str | None = None,
    catalog: CatalogIndex = Depends(get_catalog),
) -> SearchResponse:
    check_body(body)
    _check_kind(kind)
    _check_source(source)
    near = _near(near_lat, near_lon)
    outcome = search_places(
        catalog,
        q,
        limit=limit,
        kind=kind,
        feature_type=feature_type,
        source=source,
        near=near,
        region=region,
    )
    results = [
        SearchResultItem(
            score=s.score,
            match_type=s.match_type.value,
            place=place_out(s.place, regions_of_place(catalog, s.place)),
        )
        for s in outcome.scored
    ]
    return SearchResponse(
        query=q,
        normalized_query=outcome.normalized_query,
        total=outcome.total,
        results=results,
        catalog_version=catalog_version(catalog),
        coordinate_system=coordinate_system_out(),
    )


@router.get("/v1/places/reverse")
def reverse(
    lat: float,
    lon: float,
    radius_m: float = Query(default=5000.0, ge=0.0, le=500000.0),
    limit: int = Query(default=5, ge=1, le=50),
    kind: str | None = None,
    body: str | None = None,
    catalog: CatalogIndex = Depends(get_catalog),
) -> ReverseResponse:
    check_body(body)
    _check_kind(kind)
    try:
        vlat, vlon = validate_lat_lon(lat, lon)
    except ValueError as exc:
        raise OutOfRangeError(str(exc)) from exc
    outcome = reverse_lookup(
        catalog, vlat, vlon, radius_m=radius_m, limit=limit, kind=kind
    )
    nearest = [
        ReverseNearestItem(
            distance_m=round(d, 3),
            place=place_out(p, regions_of_place(catalog, p)),
        )
        for d, p in outcome.nearest
    ]
    containing = [
        ReverseContainingItem(
            place=place_out(p, regions_of_place(catalog, p)),
            containment="approximate_circle",
        )
        for p in outcome.containing
    ]
    return ReverseResponse(
        point=Center(lat=vlat, lon=vlon),
        nearest=nearest,
        containing=containing,
        regions=list(outcome.regions),
        coordinate_system=coordinate_system_out(),
    )


@router.get("/v1/places")
def list_all(
    kind: str | None = None,
    feature_type: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    region: str | None = None,
    bbox_west: float | None = None,
    bbox_south: float | None = None,
    bbox_east: float | None = None,
    bbox_north: float | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    body: str | None = None,
    catalog: CatalogIndex = Depends(get_catalog),
) -> PlaceListResponse:
    check_body(body)
    _check_kind(kind)
    _check_source(source)
    bbox_params = [bbox_west, bbox_south, bbox_east, bbox_north]
    if any(v is None for v in bbox_params) and any(v is not None for v in bbox_params):
        raise InvalidParameterError(
            "bbox_west, bbox_south, bbox_east and bbox_north must be provided together"
        )
    bbox: BboxTuple | None = None
    if all(v is not None for v in bbox_params):
        assert bbox_west is not None and bbox_south is not None
        assert bbox_east is not None and bbox_north is not None
        for name, v in (
            ("bbox_south", bbox_south),
            ("bbox_north", bbox_north),
        ):
            if not math.isfinite(v) or not -90.0 <= v <= 90.0:
                raise OutOfRangeError(f"{name} must be within [-90, 90]; got {v}")
        for name, v in (("bbox_west", bbox_west), ("bbox_east", bbox_east)):
            if not math.isfinite(v):
                raise OutOfRangeError(f"{name} must be finite; got {v}")
        bbox = (bbox_west, bbox_south, bbox_east, bbox_north)
    outcome = list_places(
        catalog,
        kind=kind,
        feature_type=feature_type,
        source=source,
        tag=tag,
        region=region,
        bbox=bbox,
        limit=limit,
        offset=offset,
    )
    return PlaceListResponse(
        total=outcome.total,
        limit=limit,
        offset=offset,
        places=[place_out(p, regions_of_place(catalog, p)) for p in outcome.places],
        coordinate_system=coordinate_system_out(),
    )


@router.get("/v1/places/{place_id}")
def get_one(place_id: str, catalog: CatalogIndex = Depends(get_catalog)) -> PlaceResponse:
    place = get_place(catalog, place_id)
    if place is None:
        raise NotFoundError(f"unknown place_id: {place_id}")
    return PlaceResponse(
        place=place_out(place, regions_of_place(catalog, place)),
        coordinate_system=coordinate_system_out(),
    )
