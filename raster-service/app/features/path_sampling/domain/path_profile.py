import math
from dataclasses import dataclass

from app.core.domain.path_sample import PathSample
from app.core.errors.exceptions import RasterValidationError


@dataclass(frozen=True)
class PathProfile:
    """Band values sampled along a path at arc-length positions.

    values[i] belongs to samples[i]; NaN is the in-domain nodata and
    out-of-extent marker — the presentation mapper converts it to null
    on the wire (D5).
    """

    band: str
    total_distance_m: float
    samples: tuple[PathSample, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.band, str) or not self.band:
            raise RasterValidationError(
                f"PathProfile band must be a non-empty string, "
                f"got {self.band!r}"
            )
        try:
            total = float(self.total_distance_m)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"PathProfile total_distance_m must be numeric, "
                f"got {self.total_distance_m!r}"
            ) from exc
        if not math.isfinite(total) or total < 0.0:
            raise RasterValidationError(
                f"PathProfile total_distance_m must be a finite number "
                f">= 0, got {total}"
            )
        object.__setattr__(self, "total_distance_m", total)
        object.__setattr__(self, "samples", tuple(self.samples))
        object.__setattr__(
            self, "values", tuple(float(v) for v in self.values)
        )
        if not self.samples:
            raise RasterValidationError(
                "PathProfile needs at least one sample"
            )
        if len(self.samples) != len(self.values):
            raise RasterValidationError(
                f"PathProfile holds {len(self.samples)} samples but "
                f"{len(self.values)} values"
            )
