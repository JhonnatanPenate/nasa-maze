from pydantic import BaseModel


class WindowPointSchema(BaseModel):
    lat: float
    lon: float


class WindowRequestSchema(BaseModel):
    """Body of `POST /raster/{dataset}/window` (spec §3.4).

    Field-level semantics (exactly one of bbox/point, required
    radius_cells, non-negative counts) are enforced by the domain
    WindowRequest so violations surface as 400; this schema only shapes
    the JSON (malformed bodies get FastAPI's 422).
    """

    band: str
    bbox: tuple[float, float, float, float] | None = None
    point: WindowPointSchema | None = None
    radius_cells: int | None = None
    halo_cells: int = 0


class WindowCoreSchema(BaseModel):
    """Slice inside `cells` that a plain bbox read would return."""

    row_off: int
    col_off: int
    rows: int
    cols: int


class WindowResolutionDegSchema(BaseModel):
    lon: float
    lat: float


class WindowResponse(BaseModel):
    """Contract for `POST /raster/{dataset}/window` (spec §4.4)."""

    band: str
    bounds: tuple[float, float, float, float]
    rows: int
    cols: int
    resolution_deg: WindowResolutionDegSchema
    center_lat: float
    core: WindowCoreSchema
    cells: list[list[float | None]]
