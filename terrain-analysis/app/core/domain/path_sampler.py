import math
from typing import Sequence

import numpy as np

from app.core.domain.distance_calculator import DistanceCalculator
from app.core.domain.geo_point import GeoPoint
from app.core.domain.path_sample import PathSample
from app.core.errors.exceptions import DomainValidationError

_ENDPOINT_REL_TOL = 1e-12
_ENDPOINT_ABS_TOL_M = 1e-6


class PathSampler:
    """Samples a polyline at regular arc-length intervals."""

    def __init__(self, distance_calculator: DistanceCalculator) -> None:
        self._distance_calculator = distance_calculator

    def sample(
        self, path: Sequence[GeoPoint], step_m: float, max_samples: int
    ) -> list[PathSample]:
        if len(path) < 2:
            raise DomainValidationError(
                f"Path needs at least 2 points, got {len(path)}"
            )
        try:
            step = float(step_m)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                f"Sample step must be numeric, got {step_m!r}"
            ) from exc
        if not math.isfinite(step) or step <= 0.0:
            raise DomainValidationError(
                f"Sample step must be a positive finite number, got {step}"
            )
        if (
            isinstance(max_samples, bool)
            or not isinstance(max_samples, int)
            or max_samples < 1
        ):
            raise DomainValidationError(
                f"max_samples must be an integer >= 1, got {max_samples!r}"
            )

        segment_lengths = np.array(
            [
                self._distance_calculator.distance_m(a, b)
                for a, b in zip(path, path[1:])
            ]
        )
        total_m = float(segment_lengths.sum())

        n_full = int(math.floor(total_m / step))
        has_tail = not math.isclose(
            n_full * step,
            total_m,
            rel_tol=_ENDPOINT_REL_TOL,
            abs_tol=_ENDPOINT_ABS_TOL_M,
        )
        expected_count = n_full + 1 + (1 if has_tail else 0)
        if expected_count > max_samples:
            raise DomainValidationError(
                f"Path requires {expected_count} samples, exceeding the limit "
                f"of {max_samples}"
            )

        positions = [k * step for k in range(n_full + 1)]
        if has_tail:
            positions.append(total_m)
        positions[-1] = total_m

        cumulative = np.concatenate(([0.0], np.cumsum(segment_lengths)))
        last_segment = len(segment_lengths) - 1
        samples: list[PathSample] = []
        for position in positions:
            segment = int(np.searchsorted(cumulative, position, side="right")) - 1
            segment = min(max(segment, 0), last_segment)
            segment_length = float(segment_lengths[segment])
            if segment_length <= 0.0:
                fraction = 0.0
            else:
                fraction = (position - float(cumulative[segment])) / segment_length
                fraction = min(max(fraction, 0.0), 1.0)
            point = self._distance_calculator.interpolate(
                path[segment], path[segment + 1], fraction
            )
            samples.append(PathSample(point=point, distance_m=position))
        return samples
