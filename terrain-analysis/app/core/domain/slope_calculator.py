import numpy as np

from app.core.domain.dem_window import DemWindow
from app.core.errors.exceptions import NoCoverageError


class SlopeCalculator:
    """Computes slope in degrees from a DEM window using Horn's method."""

    def compute(self, window: DemWindow) -> np.ndarray:
        if window.is_all_nodata():
            raise NoCoverageError("DEM window contains only nodata cells")

        z = window.elevation
        # NaN padding treats out-of-array cells like nodata. Each NaN
        # neighbour is replaced by linear extrapolation through the centre
        # from its point-mirrored opposite (n = 2*e - opposite), which is
        # exact for planar terrain, so slopes next to nodata cells or the
        # DEM edge are not attenuated. If the opposite is NaN too, the
        # centre value is used as fallback.
        p = np.pad(z, pad_width=1, mode="constant", constant_values=np.nan)
        a, b, c = p[0:-2, 0:-2], p[0:-2, 1:-1], p[0:-2, 2:]
        d, e, f = p[1:-1, 0:-2], p[1:-1, 1:-1], p[1:-1, 2:]
        g, h, i = p[2:, 0:-2], p[2:, 1:-1], p[2:, 2:]

        a_f = np.where(np.isnan(a), np.where(np.isnan(i), e, 2.0 * e - i), a)
        b_f = np.where(np.isnan(b), np.where(np.isnan(h), e, 2.0 * e - h), b)
        c_f = np.where(np.isnan(c), np.where(np.isnan(g), e, 2.0 * e - g), c)
        d_f = np.where(np.isnan(d), np.where(np.isnan(f), e, 2.0 * e - f), d)
        f_f = np.where(np.isnan(f), np.where(np.isnan(d), e, 2.0 * e - d), f)
        g_f = np.where(np.isnan(g), np.where(np.isnan(c), e, 2.0 * e - c), g)
        h_f = np.where(np.isnan(h), np.where(np.isnan(b), e, 2.0 * e - b), h)
        i_f = np.where(np.isnan(i), np.where(np.isnan(a), e, 2.0 * e - a), i)

        dz_dx = ((c_f + 2.0 * f_f + i_f) - (a_f + 2.0 * d_f + g_f)) / (
            8.0 * window.cell_size_x_m
        )
        dz_dy = ((g_f + 2.0 * h_f + i_f) - (a_f + 2.0 * b_f + c_f)) / (
            8.0 * window.cell_size_y_m
        )

        slope_deg = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
        # A cell with no real neighbour at all has unknown terrain: report
        # NaN rather than a misleading 0-degree slope.
        no_neighbours = (
            np.isnan(a) & np.isnan(b) & np.isnan(c) & np.isnan(d)
            & np.isnan(f) & np.isnan(g) & np.isnan(h) & np.isnan(i)
        )
        return np.where(np.isnan(e) | no_neighbours, np.nan, slope_deg)

    def compute_at_center(self, window: DemWindow) -> float:
        slope = self.compute(window)
        rows, cols = slope.shape
        center = float(slope[rows // 2, cols // 2])
        if np.isnan(center):
            raise NoCoverageError("Centre cell of DEM window is nodata")
        return center
