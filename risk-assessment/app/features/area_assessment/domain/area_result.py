"""Domain result of ``POST /risk/area`` grid aggregation (plan §7.1).

Additive plan extension — never alters SPEC point/path semantics. Cells
outside upstream coverage count as ``unknown`` level and are reported in
``uncovered_cells``; missing data is never scored as safe.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AreaResult:
    """Aggregate statistics over the evaluated grid cells."""

    bbox: tuple[float, float, float, float]
    cell_count: int
    cell_size_m: float
    level_counts: dict[str, int]
    blocked_fraction: float | None
    mean_score: float | None
    p95_score: float | None
    factor_stats: dict[str, dict[str, float | int | None]]
    hotspots: tuple[dict[str, object], ...]
    uncovered_cells: int
    confidence: str
    provenance: dict[str, object]
    data_quality_notes: tuple[str, ...] = field(default_factory=tuple)
    aggregation: str = "grid_cells"
    note: str = ""
