"""Row validation for the ingest pipeline (plan §8 step 3).

Sanity bands come from the Phase 0 inventory (DATA_INVENTORY_MS5.md Q4/Q9):
all delivered temperatures sit inside -150..+50 C (123.15-323.15 K), doses
are non-negative uGy/h, pressure is a plausible Mars surface value. Rows
outside a band are *rejected* and counted — never silently dropped.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# K bands: -150 C .. +50 C (Phase 0 sanity band, DATA_INVENTORY Q4).
TEMP_MIN_K = 123.15
TEMP_MAX_K = 323.15
# Mars surface pressure plausibility band (delivered: 689.9-902.2 Pa).
PRESSURE_MIN_PA = 100.0
PRESSURE_MAX_PA = 2_000.0
DOSE_MIN_Ugy_h = 0.0
UV_MIN_W_m2 = 0.0
HORA_MIN = 0
HORA_MAX = 24  # RAD hora_lmst is fractional: valid range [0, 24)

# RAD background-profile filter (Javi optimizer rule, plan §8 step 4):
# keep observations with dose_e >= RAD_KEEP_FRACTION * per-sol median.
RAD_KEEP_FRACTION = 0.7


@dataclass
class IngestReport:
    """Mutable accumulator written to ingest_report.json."""

    dataset: str
    rows_in: int = 0
    rows_kept: int = 0
    rejected: dict[str, int] = field(default_factory=dict)
    flags: list[dict[str, Any]] = field(default_factory=list)
    ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)

    def reject(self, reason: str) -> None:
        self.rejected[reason] = self.rejected.get(reason, 0) + 1

    def flag(self, period: str, note: str, severity: str = "info") -> None:
        self.flags.append(
            {"dataset": self.dataset, "period": period, "note": note, "severity": severity}
        )

    def observe(self, column: str, value: float | None) -> None:
        """Track min/max of a numeric column for the report."""
        if value is None or not math.isfinite(value):
            return
        current = self.ranges.get(column)
        if current is None:
            self.ranges[column] = (value, value)
        else:
            self.ranges[column] = (min(current[0], value), max(current[1], value))


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_finite_or_none(value: Any) -> float | None:
    """Coerce a cell to float|None; non-numeric -> None (missing)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not is_number(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def in_band(value: float | None, low: float, high: float) -> bool:
    return value is None or low <= value <= high
