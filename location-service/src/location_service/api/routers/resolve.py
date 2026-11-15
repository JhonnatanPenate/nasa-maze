"""POST /v1/resolve - main contract for Core."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from location_service.api.deps import catalog_version, get_catalog, regions_of_place
from location_service.api.schemas import (
    AlternativeOut,
    Center,
    EndpointInputIn,
    EndpointResultOut,
    ResolveRequestIn,
    ResolveResponseOut,
    coordinate_system_out,
    place_out,
)
from location_service.application.resolve_endpoints import (
    CoordinatesInput,
    EndpointInputData,
    EndpointResolution,
    ResolveOptionsData,
    resolve,
)
from location_service.ports import CatalogIndex

router = APIRouter(tags=["resolve"])


def _to_input(data: EndpointInputIn) -> EndpointInputData:
    cs = (
        {k: v for k, v in data.coordinate_system.model_dump().items() if v is not None}
        if data.coordinate_system is not None
        else None
    )
    return EndpointInputData(
        query=data.query,
        place_id=data.place_id,
        coordinates=(
            CoordinatesInput(lat=data.coordinates.lat, lon=data.coordinates.lon)
            if data.coordinates is not None
            else None
        ),
        coordinate_system=cs,
    )


def _to_input_out(data: EndpointInputData) -> dict[str, Any]:
    """Echo only the fields the client actually provided."""
    out: dict[str, Any] = {}
    if data.query is not None:
        out["query"] = data.query
    if data.place_id is not None:
        out["place_id"] = data.place_id
    if data.coordinates is not None:
        out["coordinates"] = {
            "lat": data.coordinates.lat,
            "lon": data.coordinates.lon,
        }
    if data.coordinate_system is not None:
        out["coordinate_system"] = dict(data.coordinate_system)
    return out


def _endpoint_out(res: EndpointResolution, catalog: CatalogIndex) -> EndpointResultOut:
    return EndpointResultOut(
        status=res.status,
        input=_to_input_out(res.input),
        point=(Center(lat=res.point.lat, lon=res.point.lon) if res.point is not None else None),
        place=(
            place_out(res.place, regions_of_place(catalog, res.place))
            if res.place is not None
            else None
        ),
        nearest_place=(
            place_out(res.nearest_place, regions_of_place(catalog, res.nearest_place))
            if res.nearest_place is not None
            else None
        ),
        alternatives=[
            AlternativeOut(
                score=s.score,
                match_type=s.match_type.value,
                place=place_out(s.place, regions_of_place(catalog, s.place)),
            )
            for s in res.alternatives
        ],
    )


@router.post("/v1/resolve")
def resolve_endpoint(
    body: ResolveRequestIn, catalog: CatalogIndex = Depends(get_catalog)
) -> ResolveResponseOut:
    opts_in = body.options
    opts = ResolveOptionsData(
        ambiguity_gap=opts_in.ambiguity_gap if opts_in else 0.05,
        max_alternatives=opts_in.max_alternatives if opts_in else 3,
    )
    outcome = resolve(
        catalog,
        body=body.body,
        origin=_to_input(body.origin),
        destination=_to_input(body.destination),
        options=opts,
        catalog_version=catalog_version(catalog),
    )
    return ResolveResponseOut(
        status=outcome.status,
        origin=_endpoint_out(outcome.origin, catalog),
        destination=_endpoint_out(outcome.destination, catalog),
        straight_line_distance_m=(
            round(outcome.distance_m, 3) if outcome.distance_m is not None else None
        ),
        shared_regions=list(outcome.shared_regions),
        warnings=list(outcome.warnings),
        catalog_version=outcome.catalog_version,
        coordinate_system=coordinate_system_out(),
    )
