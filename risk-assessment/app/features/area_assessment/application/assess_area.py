"""Application use case: area risk aggregation (plan extension, stub).

Phase 1 validates the request and enforces the cell cap; per-cell
evaluation lands in Phase 5. Until then the response reports structural
zeros with ``aggregation="pending"`` — never fabricated scores.
"""

import math

from app.core.domain.bounding_box import BoundingBox
from app.core.errors.exceptions import AreaTooLargeError


class AssessArea:
    """Estimate the cell count for a bbox and enforce ``max_cells``."""

    def __init__(self, max_area_cells: int) -> None:
        self._max_area_cells = max_area_cells

    def cell_count(self, bbox: BoundingBox) -> int:
        # Delivered grid resolution ~0.0015183544 deg/px (Phase 0 inventory);
        # used only for the request cap until Phase 5 evaluates cells.
        res = 0.0015183544372303697
        cols = math.ceil((bbox.max_lon - bbox.min_lon) / res)
        rows = math.ceil((bbox.max_lat - bbox.min_lat) / res)
        return cols * rows

    def check_cap(self, bbox: BoundingBox, max_cells: int | None) -> int:
        cap = self._max_area_cells if max_cells is None else int(max_cells)
        count = self.cell_count(bbox)
        if count > cap:
            raise AreaTooLargeError(f"Area spans ~{count} cells, exceeding max_cells={cap}")
        return count
