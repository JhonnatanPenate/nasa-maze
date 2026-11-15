"""GET /v1/regions - known regions / AOIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from location_service.api.deps import get_catalog
from location_service.api.schemas import (
    BboxOut,
    RegionOut,
    RegionsResponse,
    coordinate_system_out,
)
from location_service.ports import CatalogIndex

router = APIRouter(tags=["regions"])


@router.get("/v1/regions")
def list_regions(catalog: CatalogIndex = Depends(get_catalog)) -> RegionsResponse:
    regions = []
    for r in catalog.regions():
        bbox = None
        if r.bbox is not None:
            bbox = BboxOut(
                west=r.bbox.west, south=r.bbox.south, east=r.bbox.east, north=r.bbox.north
            )
        regions.append(
            RegionOut(id=r.id, name=r.name, kind=r.kind, bbox=bbox, source=r.source, note=r.note)
        )
    return RegionsResponse(regions=regions, coordinate_system=coordinate_system_out())
