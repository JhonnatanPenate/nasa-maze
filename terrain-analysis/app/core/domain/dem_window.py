import math
from dataclasses import dataclass

import numpy as np

from app.core.errors.exceptions import DomainValidationError


@dataclass(frozen=True)
class DemWindow:
    """A rectangular DEM extract. Nodata cells are represented as NaN."""

    elevation: np.ndarray
    cell_size_x_m: float
    cell_size_y_m: float

    def __post_init__(self) -> None:
        try:
            elevation = np.asarray(self.elevation, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                "DemWindow elevation must be a numeric 2-D array"
            ) from exc
        if elevation.ndim != 2 or 0 in elevation.shape:
            raise DomainValidationError(
                f"DemWindow elevation must be a non-empty 2-D array, "
                f"got shape {elevation.shape}"
            )
        object.__setattr__(self, "elevation", elevation)
        for name in ("cell_size_x_m", "cell_size_y_m"):
            try:
                value = float(getattr(self, name))
            except (TypeError, ValueError) as exc:
                raise DomainValidationError(
                    f"DemWindow {name} must be numeric, got {getattr(self, name)!r}"
                ) from exc
            if not math.isfinite(value) or value <= 0.0:
                raise DomainValidationError(
                    f"DemWindow {name} must be a positive finite number, got {value}"
                )
            object.__setattr__(self, name, value)

    def is_all_nodata(self) -> bool:
        return bool(np.isnan(self.elevation).all())

    def center_value(self) -> float:
        rows, cols = self.elevation.shape
        return float(self.elevation[rows // 2, cols // 2])
