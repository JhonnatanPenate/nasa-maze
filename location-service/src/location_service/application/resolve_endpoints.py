"""Use case: POST /v1/resolve - resolve origin and destination (section 6.5)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from location_service.domain.geo import (
    CANONICAL_BODY,
    CANONICAL_CRS,
    CANONICAL_LAT_TYPE,
    CANONICAL_LON_CONVENTION,
    MARSV_RADIUS_M,
    haversine_m,
    validate_lat_lon,
)
from location_service.domain.models import Coordinate, Place
from location_service.domain.ranking import MatchType, ScoredPlace, is_ambiguous
from location_service.errors import (
    InvalidParameterError,
    OutOfRangeError,
    UnsupportedBodyError,
    UnsupportedCoordinateSystemError,
)
from location_service.ports import CatalogIndex

_NEAREST_PLACE_RADIUS_M = 5_000.0
_CO_LOCATED_RADIUS_M = 10.0
_SAME_POINT_RADIUS_M = 1.0
_LOW_CONFIDENCE_SCORE = 0.9

# global status severity when neither endpoint resolved (documented choice)
_STATUS_SEVERITY = {"invalid": 3, "not_found": 2, "ambiguous": 1, "resolved": 0, "partial": 0}


@dataclass(frozen=True)
class CoordinatesInput:
    lat: float
    lon: float


@dataclass(frozen=True)
class EndpointInputData:
    query: str | None = None
    place_id: str | None = None
    coordinates: CoordinatesInput | None = None
    coordinate_system: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ResolveOptionsData:
    ambiguity_gap: float = 0.05
    max_alternatives: int = 3


@dataclass(frozen=True)
class EndpointResolution:
    status: str  # resolved | ambiguous | not_found | invalid
    input: EndpointInputData
    point: Coordinate | None
    place: Place | None
    nearest_place: Place | None
    alternatives: tuple[ScoredPlace, ...]
    low_confidence: bool
    regions: tuple[str, ...]


@dataclass(frozen=True)
class ResolveOutcome:
    status: str
    origin: EndpointResolution
    destination: EndpointResolution
    distance_m: float | None
    shared_regions: tuple[str, ...]
    warnings: tuple[str, ...]
    catalog_version: str


def check_body(body: str | None) -> None:
    if body is not None and body != CANONICAL_BODY:
        raise UnsupportedBodyError(f"body must be '{CANONICAL_BODY}'; got {body!r}")


def _check_coordinate_system(declared: Mapping[str, object] | None) -> None:
    """Reject client-declared conventions that differ from the canonical one."""
    if not declared:
        return
    canonical = {
        "body": CANONICAL_BODY,
        "crs": CANONICAL_CRS,
        "lat_type": CANONICAL_LAT_TYPE,
        "lon_convention": CANONICAL_LON_CONVENTION,
        "radius_m": MARSV_RADIUS_M,
    }
    for key, expected in canonical.items():
        if key in declared and declared[key] != expected:
            raise UnsupportedCoordinateSystemError(
                f"coordinate_system.{key}={declared[key]!r} differs from canonical "
                f"{expected!r}"
            )


def _endpoint_regions(index: CatalogIndex, point: Coordinate | None) -> tuple[str, ...]:
    if point is None:
        return ()
    return tuple(index.regions_containing(point.lat, point.lon))


def _resolve_query(
    index: CatalogIndex,
    query: str,
    *,
    ambiguity_gap: float,
    max_alternatives: int,
) -> EndpointResolution:
    scored = index.rank(query)
    if not scored:
        return EndpointResolution(
            "not_found",
            EndpointInputData(query=query),
            None,
            None,
            None,
            (),
            False,
            (),
        )
    if is_ambiguous(scored, ambiguity_gap):
        return EndpointResolution(
            "ambiguous",
            EndpointInputData(query=query),
            None,
            None,
            None,
            tuple(scored[:max_alternatives]),
            False,
            (),
        )
    top = scored[0]
    low_conf = top.match_type == MatchType.FUZZY and top.score < _LOW_CONFIDENCE_SCORE
    point = Coordinate(lat=top.place.center.lat, lon=top.place.center.lon)
    return EndpointResolution(
        "resolved",
        EndpointInputData(query=query),
        point,
        top.place,
        None,
        (),
        low_conf,
        _endpoint_regions(index, point),
    )


def _resolve_place_id(index: CatalogIndex, place_id: str) -> EndpointResolution:
    place = index.get(place_id)
    if place is None:
        return EndpointResolution(
            "not_found",
            EndpointInputData(place_id=place_id),
            None,
            None,
            None,
            (),
            False,
            (),
        )
    point = Coordinate(lat=place.center.lat, lon=place.center.lon)
    return EndpointResolution(
        "resolved",
        EndpointInputData(place_id=place_id),
        point,
        place,
        None,
        (),
        False,
        _endpoint_regions(index, point),
    )


def _resolve_coordinates(
    index: CatalogIndex, coordinates: CoordinatesInput
) -> EndpointResolution:
    try:
        lat, lon = validate_lat_lon(coordinates.lat, coordinates.lon)
    except ValueError as exc:
        raise OutOfRangeError(str(exc)) from exc
    point = Coordinate(lat=lat, lon=lon)
    nearest = index.nearest_within(lat, lon, _NEAREST_PLACE_RADIUS_M)
    nearest_place = nearest[0][1] if nearest else None
    return EndpointResolution(
        "resolved",
        EndpointInputData(coordinates=coordinates),
        point,
        None,
        nearest_place,
        (),
        False,
        _endpoint_regions(index, point),
    )


def resolve_endpoint(
    index: CatalogIndex,
    endpoint: EndpointInputData,
    *,
    ambiguity_gap: float,
    max_alternatives: int,
) -> EndpointResolution:
    """Resolve one endpoint. Raises AppError subclasses for malformed input."""
    _check_coordinate_system(endpoint.coordinate_system)
    provided = [
        name
        for name, value in (
            ("query", endpoint.query),
            ("place_id", endpoint.place_id),
            ("coordinates", endpoint.coordinates),
        )
        if value is not None
    ]
    if len(provided) != 1:
        raise InvalidParameterError(
            "each endpoint must provide exactly one of query, place_id or "
            f"coordinates; got {provided or 'none'}"
        )
    if endpoint.query is not None:
        if not endpoint.query.strip():
            raise InvalidParameterError("query must not be empty")
        res = _resolve_query(
            index,
            endpoint.query,
            ambiguity_gap=ambiguity_gap,
            max_alternatives=max_alternatives,
        )
    elif endpoint.place_id is not None:
        res = _resolve_place_id(index, endpoint.place_id)
    else:
        assert endpoint.coordinates is not None
        res = _resolve_coordinates(index, endpoint.coordinates)
    # echo the original request input (incl. declared coordinate_system)
    return replace(res, input=endpoint)


def _worse_status(a: str, b: str) -> str:
    return a if _STATUS_SEVERITY.get(a, 0) >= _STATUS_SEVERITY.get(b, 0) else b


def resolve(
    index: CatalogIndex,
    *,
    body: str | None,
    origin: EndpointInputData,
    destination: EndpointInputData,
    options: ResolveOptionsData,
    catalog_version: str,
) -> ResolveOutcome:
    check_body(body)
    origin_r = resolve_endpoint(
        index, origin, ambiguity_gap=options.ambiguity_gap,
        max_alternatives=options.max_alternatives,
    )
    destination_r = resolve_endpoint(
        index, destination, ambiguity_gap=options.ambiguity_gap,
        max_alternatives=options.max_alternatives,
    )

    warnings: list[str] = []

    def warn(code: str) -> None:
        if code not in warnings:
            warnings.append(code)

    if (
        origin_r.point is not None
        and not origin_r.regions
    ):
        warn("OUTSIDE_KNOWN_AOI")
    if (
        destination_r.point is not None
        and not destination_r.regions
    ):
        warn("OUTSIDE_KNOWN_AOI")

    distance_m: float | None = None
    shared_regions: tuple[str, ...] = ()
    both_resolved = origin_r.status == "resolved" and destination_r.status == "resolved"
    if both_resolved:
        assert origin_r.point is not None and destination_r.point is not None
        distance_m = haversine_m(
            origin_r.point.lat, origin_r.point.lon,
            destination_r.point.lat, destination_r.point.lon,
        )
        o_regs, d_regs = set(origin_r.regions), set(destination_r.regions)
        if o_regs and d_regs and o_regs.isdisjoint(d_regs):
            warn("ENDPOINTS_IN_DIFFERENT_REGIONS")
        shared_regions = tuple(sorted(o_regs & d_regs))
        if distance_m < _SAME_POINT_RADIUS_M:
            warn("SAME_POINT")

    for res in (origin_r, destination_r):
        if res.point is None:
            continue
        exclude = res.place.id if res.place is not None else None
        if index.co_located(
            res.point.lat, res.point.lon, exclude_id=exclude, within_m=_CO_LOCATED_RADIUS_M
        ):
            warn("CO_LOCATED_PLACES")

    if origin_r.low_confidence or destination_r.low_confidence:
        warn("LOW_CONFIDENCE_MATCH")

    if both_resolved:
        status = "resolved"
    elif origin_r.status == "resolved" or destination_r.status == "resolved":
        status = "partial"
    else:
        status = _worse_status(origin_r.status, destination_r.status)

    return ResolveOutcome(
        status=status,
        origin=origin_r,
        destination=destination_r,
        distance_m=distance_m,
        shared_regions=shared_regions,
        warnings=tuple(warnings),
        catalog_version=catalog_version,
    )
