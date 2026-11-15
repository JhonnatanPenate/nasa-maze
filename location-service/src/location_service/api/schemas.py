"""Pydantic API schemas - mirror of packages/contracts/location-service/openapi.yaml."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from location_service.domain.geo import canonical_coordinate_system
from location_service.domain.models import Bbox, Place


class CoordinateSystemOut(BaseModel):
    body: str
    crs: str
    lat_type: str
    lon_convention: str
    radius_m: int


class Center(BaseModel):
    lat: float
    lon: float


class BboxOut(BaseModel):
    west: float
    south: float
    east: float
    north: float


class PlaceOut(BaseModel):
    id: str
    name: str
    body: str
    kind: str
    feature_type: str
    source: str
    center: Center
    bbox: BboxOut | None
    diameter_km: float | None
    elevation_m: float | None
    approval_status: str | None
    aliases: list[str]
    tags: list[str]
    properties: dict[str, Any]
    in_regions: list[str]


class HealthStatus(BaseModel):
    status: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str


class SearchResultItem(BaseModel):
    score: float
    match_type: str
    place: PlaceOut


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    total: int
    results: list[SearchResultItem]
    catalog_version: str
    coordinate_system: CoordinateSystemOut


class ReverseNearestItem(BaseModel):
    distance_m: float
    place: PlaceOut


class ReverseContainingItem(BaseModel):
    place: PlaceOut
    containment: str


class ReverseResponse(BaseModel):
    point: Center
    nearest: list[ReverseNearestItem]
    containing: list[ReverseContainingItem]
    regions: list[str]
    coordinate_system: CoordinateSystemOut


class PlaceListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    places: list[PlaceOut]
    coordinate_system: CoordinateSystemOut


class PlaceResponse(BaseModel):
    place: PlaceOut
    coordinate_system: CoordinateSystemOut


# ---- resolve request models ----


class CoordinatesInputIn(BaseModel):
    lat: float
    lon: float


class CoordinateSystemIn(BaseModel):
    body: str | None = None
    crs: str | None = None
    lat_type: str | None = None
    lon_convention: str | None = None
    radius_m: int | None = None


class EndpointInputIn(BaseModel):
    query: str | None = Field(default=None, min_length=1, max_length=100)
    place_id: str | None = Field(default=None, min_length=1)
    coordinates: CoordinatesInputIn | None = None
    coordinate_system: CoordinateSystemIn | None = None


class ResolveOptionsIn(BaseModel):
    ambiguity_gap: float = Field(default=0.05, ge=0.0, le=1.0)
    max_alternatives: int = Field(default=3, ge=1, le=10)


class ResolveRequestIn(BaseModel):
    body: str = "mars"
    origin: EndpointInputIn
    destination: EndpointInputIn
    options: ResolveOptionsIn | None = None


# ---- resolve response models ----


class AlternativeOut(BaseModel):
    score: float
    match_type: str
    place: PlaceOut


class EndpointResultOut(BaseModel):
    status: str
    input: dict[str, Any]
    point: Center | None
    place: PlaceOut | None
    nearest_place: PlaceOut | None = None
    alternatives: list[AlternativeOut]


class ResolveResponseOut(BaseModel):
    status: str
    origin: EndpointResultOut
    destination: EndpointResultOut
    straight_line_distance_m: float | None
    shared_regions: list[str]
    warnings: list[str]
    catalog_version: str
    coordinate_system: CoordinateSystemOut


# ---- regions / meta ----


class RegionOut(BaseModel):
    id: str
    name: str
    kind: str
    bbox: BboxOut | None
    source: str
    note: str | None


class RegionsResponse(BaseModel):
    regions: list[RegionOut]
    coordinate_system: CoordinateSystemOut


class CatalogMetaResponse(BaseModel):
    catalog_version: str
    built_at: str
    schema_version: int
    sources: dict[str, str]
    counts: dict[str, Any]
    coordinate_system: CoordinateSystemOut


class FeatureTypeCount(BaseModel):
    feature_type: str
    count: int


class FeatureTypesResponse(BaseModel):
    feature_types: list[FeatureTypeCount]


class ReloadResponse(BaseModel):
    status: str
    catalog_version: str


# ---- serializers ----


def coordinate_system_out() -> CoordinateSystemOut:
    return CoordinateSystemOut(**canonical_coordinate_system())  # type: ignore[arg-type]


def place_out(place: Place, in_regions: list[str]) -> PlaceOut:
    bbox: BboxOut | None = None
    if place.bbox is not None:
        b: Bbox = place.bbox
        bbox = BboxOut(west=b.west, south=b.south, east=b.east, north=b.north)
    return PlaceOut(
        id=place.id,
        name=place.name,
        body=place.body,
        kind=place.kind,
        feature_type=place.feature_type,
        source=place.source,
        center=Center(lat=place.center.lat, lon=place.center.lon),
        bbox=bbox,
        diameter_km=place.diameter_km,
        elevation_m=place.elevation_m,
        approval_status=place.approval_status,
        aliases=list(place.aliases),
        tags=list(place.tags),
        properties=place.properties,
        in_regions=in_regions,
    )
