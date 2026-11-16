from typing import Any

from pydantic import BaseModel, Field


class AreaRequest(BaseModel):
    """Plan extension `POST /risk/area` (plan §7.1)."""

    body: str = "mars"
    bbox: list[float] = Field(min_length=4, max_length=4)
    sol: int | None = None
    hora: int = 12
    vehicle_profile: str | None = None
    max_cells: int | None = None


class AreaResponse(BaseModel):
    """Plan extension area aggregate: statistics over the evaluated grid
    cells — never a per-cell raster."""

    bbox: list[float]
    cell_count: int
    cell_size_m: float | None
    level_counts: dict[str, int]
    blocked_fraction: float | None
    mean_score: float | None
    p95_score: float | None
    factor_stats: dict[str, Any]
    hotspots: list[dict[str, Any]]
    aggregation: str
    note: str
    # Additive explainability fields (same convention as point/path).
    confidence: str | None = None
    uncovered_cells: int = 0
    provenance: dict[str, Any] = Field(default_factory=dict)
    data_quality_notes: list[str] = Field(default_factory=list)
