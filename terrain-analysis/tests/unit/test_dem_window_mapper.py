import math

import numpy as np
import pytest

from app.core.errors.exceptions import DomainValidationError
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper

RADIUS_M = 3_389_500.0
DEG_TO_M = math.pi / 180.0


@pytest.fixture
def mapper() -> DemWindowMapper:
    return DemWindowMapper(RADIUS_M)


class TestToDemWindow:
    def test_converts_degrees_to_metres(self, mapper: DemWindowMapper) -> None:
        window = mapper.to_dem_window(
            raw=np.array([[0, 1], [2, 3]]),
            nodata=None,
            res_lon_deg=0.02,
            res_lat_deg=0.01,
            center_lat_deg=60.0,
        )
        # res_lon*cos(60) == res_lat, so both cell sizes are equal.
        expected = 0.01 * DEG_TO_M * RADIUS_M
        assert window.cell_size_y_m == pytest.approx(expected)
        assert window.cell_size_x_m == pytest.approx(expected)

    def test_elevation_cast_to_float64(self, mapper: DemWindowMapper) -> None:
        window = mapper.to_dem_window(
            raw=np.array([[1, 2], [3, 4]], dtype=np.int32),
            nodata=None,
            res_lon_deg=0.01,
            res_lat_deg=0.01,
            center_lat_deg=0.0,
        )
        assert window.elevation.dtype == np.float64
        np.testing.assert_array_equal(
            window.elevation, np.array([[1.0, 2.0], [3.0, 4.0]])
        )

    def test_nodata_and_non_finite_become_nan(
        self, mapper: DemWindowMapper
    ) -> None:
        window = mapper.to_dem_window(
            raw=np.array([[1.0, -999.0], [np.inf, np.nan]]),
            nodata=-999.0,
            res_lon_deg=0.01,
            res_lat_deg=0.01,
            center_lat_deg=0.0,
        )
        assert window.elevation[0, 0] == 1.0
        assert np.isnan(window.elevation[0, 1])
        assert np.isnan(window.elevation[1, 0])
        assert np.isnan(window.elevation[1, 1])

    def test_nodata_compared_in_native_dtype(
        self, mapper: DemWindowMapper
    ) -> None:
        # -32767.1 is not exactly representable as float32: the sentinel
        # stored in a float32 raster is float32(nodata), so the comparison
        # must happen in the array's native dtype.
        nodata = -32767.1
        raw = np.array([[1.0, nodata], [2.0, 3.0]], dtype=np.float32)
        assert float(raw[0, 1]) != nodata
        window = mapper.to_dem_window(
            raw=raw,
            nodata=nodata,
            res_lon_deg=0.01,
            res_lat_deg=0.01,
            center_lat_deg=0.0,
        )
        assert window.elevation[0, 0] == 1.0
        assert np.isnan(window.elevation[0, 1])

    def test_polar_latitude_floors_cell_size_x(
        self, mapper: DemWindowMapper
    ) -> None:
        window = mapper.to_dem_window(
            raw=np.array([[1.0]]),
            nodata=None,
            res_lon_deg=0.01,
            res_lat_deg=0.01,
            center_lat_deg=90.0,
        )
        assert math.isfinite(window.cell_size_x_m)
        assert window.cell_size_x_m > 0.0

    def test_non_2d_raw_raises(self, mapper: DemWindowMapper) -> None:
        with pytest.raises(DomainValidationError):
            mapper.to_dem_window(
                raw=np.array([1.0, 2.0, 3.0]),
                nodata=None,
                res_lon_deg=0.01,
                res_lat_deg=0.01,
                center_lat_deg=0.0,
            )
