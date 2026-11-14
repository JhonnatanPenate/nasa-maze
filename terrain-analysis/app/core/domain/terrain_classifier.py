import math

from app.core.domain.terrain_class import TerrainClass
from app.core.errors.exceptions import DomainValidationError


class TerrainClassifier:
    def __init__(
        self,
        flat_max_deg: float = 5.0,
        moderate_max_deg: float = 15.0,
        steep_max_deg: float = 30.0,
    ) -> None:
        thresholds = (flat_max_deg, moderate_max_deg, steep_max_deg)
        try:
            valid = all(math.isfinite(t) and t > 0.0 for t in thresholds)
        except TypeError as exc:
            raise DomainValidationError(
                f"Slope thresholds must be numeric, got {thresholds!r}"
            ) from exc
        if not valid:
            raise DomainValidationError(
                f"Slope thresholds must be positive finite numbers, got {thresholds}"
            )
        if not (flat_max_deg < moderate_max_deg < steep_max_deg):
            raise DomainValidationError(
                f"Slope thresholds must be strictly increasing, got {thresholds}"
            )
        self._flat_max_deg = flat_max_deg
        self._moderate_max_deg = moderate_max_deg
        self._steep_max_deg = steep_max_deg

    @property
    def steep_min_deg(self) -> float:
        """Lower bound of the `steep` terrain class."""
        return self._moderate_max_deg

    def classify(self, slope_deg: float) -> TerrainClass:
        try:
            finite = math.isfinite(slope_deg)
        except TypeError as exc:
            raise DomainValidationError(
                f"Slope must be numeric, got {slope_deg!r}"
            ) from exc
        if not finite or slope_deg < 0.0:
            raise DomainValidationError(
                f"Slope must be a non-negative finite number, got {slope_deg!r}"
            )
        if slope_deg < self._flat_max_deg:
            return TerrainClass.FLAT
        if slope_deg < self._moderate_max_deg:
            return TerrainClass.MODERATE
        if slope_deg < self._steep_max_deg:
            return TerrainClass.STEEP
        return TerrainClass.HAZARDOUS
