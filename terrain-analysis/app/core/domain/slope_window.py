import math
from dataclasses import dataclass

import numpy as np

from app.core.errors.exceptions import DomainValidationError


@dataclass(frozen=True)
class SlopeWindow:
    """A rectangular extract of pre-computed slope in degrees. Nodata cells
    are represented as NaN."""

    slope_deg: np.ndarray
    cell_size_x_m: float
    cell_size_y_m: float

    def __post_init__(self) -> None:
        try:
            slope_deg = np.asarray(self.slope_deg, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                "SlopeWindow slope_deg must be a numeric 2-D array"
            ) from exc
        if slope_deg.ndim != 2 or 0 in slope_deg.shape:
            raise DomainValidationError(
                f"SlopeWindow slope_deg must be a non-empty 2-D array, "
                f"got shape {slope_deg.shape}"
            )
        object.__setattr__(self, "slope_deg", slope_deg)
        for name in ("cell_size_x_m", "cell_size_y_m"):
            try:
                value = float(getattr(self, name))
            except (TypeError, ValueError) as exc:
                raise DomainValidationError(
                    f"SlopeWindow {name} must be numeric, got {getattr(self, name)!r}"
                ) from exc
            if not math.isfinite(value) or value <= 0.0:
                raise DomainValidationError(
                    f"SlopeWindow {name} must be a positive finite number, got {value}"
                )
            object.__setattr__(self, name, value)

    def is_all_nodata(self) -> bool:
        return bool(np.isnan(self.slope_deg).all())

    def center_value(self) -> float:
        rows, cols = self.slope_deg.shape
        return float(self.slope_deg[rows // 2, cols // 2])

    def valid_values(self) -> np.ndarray:
        return self.slope_deg[np.isfinite(self.slope_deg)]
