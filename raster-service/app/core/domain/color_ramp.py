import math

import numpy as np

from app.core.errors.exceptions import RasterValidationError

_STOPS: dict[str, tuple[tuple[int, int, int, int], ...]] = {
    "slope": ((0, 128, 0, 255), (255, 255, 0, 255), (255, 0, 0, 255)),
    "viridis": (
        (68, 1, 84, 255),
        (59, 82, 139, 255),
        (33, 145, 140, 255),
        (94, 201, 98, 255),
        (253, 231, 37, 255),
    ),
    "grayscale": ((0, 0, 0, 255), (255, 255, 255, 255)),
}


class ColorRamp:
    """Maps a 2D float array plus a (min, max) range to a uint8 RGBA image.

    Non-finite cells (NaN, +/-inf) become fully transparent pixels; a
    constant range maps every finite cell to the mid-ramp colour.
    """

    def __init__(self, name: str) -> None:
        if name not in _STOPS:
            raise RasterValidationError(
                f"Unknown colormap {name!r}. Valid colormaps: "
                f"{', '.join(self.names())}"
            )
        self._name = name
        self._stops = np.array(_STOPS[name], dtype=np.float64)

    @property
    def name(self) -> str:
        return self._name

    @staticmethod
    def names() -> list[str]:
        return list(_STOPS)

    def render(
        self, values: np.ndarray, value_min: float, value_max: float
    ) -> np.ndarray:
        arr = np.asarray(values, dtype=np.float64)
        if arr.ndim != 2:
            raise RasterValidationError(
                f"ColorRamp.render needs a 2D array, got {arr.ndim}D"
            )
        try:
            low = float(value_min)
            high = float(value_max)
        except (TypeError, ValueError) as exc:
            raise RasterValidationError(
                f"Value range must be numeric, got ({value_min!r}, {value_max!r})"
            ) from exc
        if not math.isfinite(low) or not math.isfinite(high):
            raise RasterValidationError(
                f"Value range must be finite, got ({low}, {high})"
            )
        if high < low:
            raise RasterValidationError(
                f"Value range min ({low}) must not exceed max ({high})"
            )

        finite = np.isfinite(arr)
        span = high - low
        if span == 0.0:
            t = np.full(arr.shape, 0.5)
        else:
            t = (arr - low) / span
        t = np.clip(t, 0.0, 1.0)

        positions = np.linspace(0.0, 1.0, len(self._stops))
        rgba = np.empty(arr.shape + (4,), dtype=np.float64)
        for channel in range(4):
            rgba[..., channel] = np.interp(
                t, positions, self._stops[:, channel]
            )
        rgba[~finite] = 0.0
        return np.round(rgba).astype(np.uint8)
