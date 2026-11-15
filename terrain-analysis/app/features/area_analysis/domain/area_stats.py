import math
from dataclasses import dataclass

from app.core.errors.exceptions import DomainValidationError
from app.features.area_analysis.domain.value_stats import ValueStats


@dataclass(frozen=True)
class AreaStats:
    """Aggregate statistics over a DEM window: the result of POST
    /terrain/area.

    steep_fraction is the share of cells with computable slope that fall
    into the `steep` or `hazardous` terrain classes (slope >= the lower
    bound of the `steep` class).
    """

    elevation_m: ValueStats | None
    slope_deg: ValueStats
    steep_fraction: float

    def __post_init__(self) -> None:
        if self.elevation_m is not None and not isinstance(
            self.elevation_m, ValueStats
        ):
            raise DomainValidationError(
                f"AreaStats field elevation_m must be a ValueStats or None, "
                f"got {self.elevation_m!r}"
            )
        if not isinstance(self.slope_deg, ValueStats):
            raise DomainValidationError(
                f"AreaStats field slope_deg must be a ValueStats, "
                f"got {self.slope_deg!r}"
            )
        try:
            fraction = float(self.steep_fraction)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                f"AreaStats steep_fraction must be numeric, "
                f"got {self.steep_fraction!r}"
            ) from exc
        if not math.isfinite(fraction) or not (0.0 <= fraction <= 1.0):
            raise DomainValidationError(
                f"AreaStats steep_fraction must lie in [0, 1], "
                f"got {fraction}"
            )
        object.__setattr__(self, "steep_fraction", fraction)
