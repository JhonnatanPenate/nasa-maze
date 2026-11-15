from pydantic import BaseModel


class DatasetItemResponse(BaseModel):
    name: str
    path: str
    readable: bool


class DatasetsResponse(BaseModel):
    """Contract for `GET /raster/datasets` (spec §4.1)."""

    datasets: list[DatasetItemResponse]


class BandResponse(BaseModel):
    index: int
    name: str
    unit: str
    nodata: float | None


class ResolutionDegResponse(BaseModel):
    lon: float
    lat: float


class MetadataResponse(BaseModel):
    """Contract for `GET /raster/{dataset}/metadata` (spec §4.2)."""

    name: str
    crs: str
    bounds: list[float]
    width: int
    height: int
    resolution_deg: ResolutionDegResponse
    resolution_m: float
    bands: list[BandResponse]
