import math
from dataclasses import dataclass

from app.core.errors.exceptions import DomainValidationError


@dataclass(frozen=True)
class ValueStats:
    """Min/max/mean aggregate over the valid cells of one quantity."""

    min: float
    max: float
    mean: float

    def __post_init__(self) -> None:
        values = {}
        for name in ("min", "max", "mean"):
            try:
                values[name] = float(getattr(self, name))
            except (TypeError, ValueError) as exc:
                raise DomainValidationError(
                    f"ValueStats field {name} must be numeric, "
                    f"got {getattr(self, name)!r}"
                ) from exc
            if not math.isfinite(values[name]):
                raise DomainValidationError(
                    f"ValueStats field {name} must be finite, "
                    f"got {values[name]}"
                )
            object.__setattr__(self, name, values[name])
        if self.min > self.max:
            raise DomainValidationError(
                f"ValueStats min ({self.min}) must not exceed "
                f"max ({self.max})"
            )
