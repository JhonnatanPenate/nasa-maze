import math

import numpy as np

from app.core.domain.dem_window import DemWindow
from app.core.errors.exceptions import DomainValidationError

_DEG_TO_RAD = math.pi / 180.0
# Floor on |cos(lat)| so cell_size_x_m stays finite near the poles.
# Proper polar handling (e.g. a projected CRS) is out of MVP scope;
# this only guards against non-finite cell sizes.
_MIN_COS_LAT = 1e-6


class DemWindowMapper:
    """Adapter converting raw raster payloads into DemWindow domain objects.

    This is the only place where angular (degree) cell sizes are converted
    to metres, using the configured body radius. Nodata sentinels and
    non-finite values are normalised to NaN.
    """

    def __init__(self, planet_radius_m: float) -> None:
        try:
            radius = float(planet_radius_m)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError(
                f"Planet radius must be numeric, got {planet_radius_m!r}"
            ) from exc
        if not math.isfinite(radius) or radius <= 0.0:
            raise DomainValidationError(
                f"Planet radius must be a positive finite number, got {radius}"
            )
        self._planet_radius_m = radius

    def to_dem_window(
        self,
        raw: np.ndarray,
        nodata: float | None,
        res_lon_deg: float,
        res_lat_deg: float,
        center_lat_deg: float,
    ) -> DemWindow:
        raw_array = np.asarray(raw)
        nodata_mask = np.zeros(raw_array.shape, dtype=bool)
        if nodata is not None and math.isfinite(float(nodata)):
            # Compare in the array's native dtype: a sentinel stored in a
            # float32 raster is float32(nodata), which generally differs
            # from the float64 tag value.
            try:
                nodata_native = raw_array.dtype.type(float(nodata))
                nodata_mask = raw_array == nodata_native
            except (TypeError, ValueError, OverflowError):
                nodata_mask = np.zeros(raw_array.shape, dtype=bool)
        elevation = np.asarray(raw_array, dtype=np.float64)
        nodata_mask = nodata_mask | ~np.isfinite(elevation)
        elevation = np.where(nodata_mask, np.nan, elevation)

        # Metric cell size on a sphere: latitude degrees are uniform, the
        # longitude degree shrinks with cos(lat) towards the poles.
        cell_size_y_m = res_lat_deg * _DEG_TO_RAD * self._planet_radius_m
        cos_lat = math.cos(center_lat_deg * _DEG_TO_RAD)
        cell_size_x_m = (
            res_lon_deg
            * _DEG_TO_RAD
            * self._planet_radius_m
            * max(abs(cos_lat), _MIN_COS_LAT)
        )
        return DemWindow(
            elevation=elevation,
            cell_size_x_m=cell_size_x_m,
            cell_size_y_m=cell_size_y_m,
        )
