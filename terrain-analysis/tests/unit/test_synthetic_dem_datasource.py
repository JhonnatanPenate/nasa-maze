import math

import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DomainValidationError,
    NoCoverageError,
)
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.synthetic_dem_datasource import (
    SyntheticDemDatasource,
)

RADIUS_M = 3_389_500.0


@pytest.fixture
def mapper() -> DemWindowMapper:
    return DemWindowMapper(RADIUS_M)


@pytest.fixture
def default_ds(mapper: DemWindowMapper) -> SyntheticDemDatasource:
    return SyntheticDemDatasource.default(mapper, max_window_cells=4_000_000)


class TestDefaultDem:
    @pytest.mark.parametrize("lat, lon", [(18.4, 77.5), (18.5, 77.6)])
    def test_smoke_coordinates_have_data(
        self, default_ds: SyntheticDemDatasource, lat: float, lon: float
    ) -> None:
        window = default_ds.read_window_around(GeoPoint(lat=lat, lon=lon), 0)
        assert math.isfinite(window.center_value())

    def test_nodata_hole_is_nan(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        # The documented hole: lon 77.90..77.95, lat 18.90..18.95.
        window = default_ds.read_window_around(
            GeoPoint(lat=18.925, lon=77.925), 0
        )
        assert np.isnan(window.center_value())

    def test_window_fully_inside_hole_is_all_nodata(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        window = default_ds.read_window(
            BoundingBox(
                min_lon=77.905, min_lat=18.905, max_lon=77.945, max_lat=18.945
            )
        )
        assert window.is_all_nodata()


class TestReadWindow:
    def test_window_shape_and_cell_sizes(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        # 0.2x0.2 degrees at 1/1200 degree per cell -> 240x240 cells.
        window = default_ds.read_window(
            BoundingBox(min_lon=77.4, min_lat=18.4, max_lon=77.6, max_lat=18.6)
        )
        assert window.elevation.shape == (240, 240)
        assert window.cell_size_y_m == pytest.approx(
            math.pi / 180.0 * RADIUS_M / 1200.0
        )
        assert window.cell_size_x_m == pytest.approx(
            math.pi / 180.0 * RADIUS_M / 1200.0 * math.cos(math.radians(18.5))
        )
        assert np.isfinite(window.elevation).all()

    def test_non_intersecting_bbox_raises(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        with pytest.raises(NoCoverageError):
            default_ds.read_window(
                BoundingBox(
                    min_lon=70.0, min_lat=10.0, max_lon=71.0, max_lat=11.0
                )
            )

    def test_tiny_bbox_returns_single_cell(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        window = default_ds.read_window(
            BoundingBox(
                min_lon=77.4999,
                min_lat=18.4999,
                max_lon=77.5001,
                max_lat=18.5001,
            )
        )
        assert window.elevation.shape == (1, 1)

    def test_max_window_cells_raises_before_read(
        self, mapper: DemWindowMapper
    ) -> None:
        ds = SyntheticDemDatasource.default(mapper, max_window_cells=10)
        with pytest.raises(DomainValidationError):
            ds.read_window(
                BoundingBox(min_lon=77.0, min_lat=18.0, max_lon=78.0, max_lat=19.0)
            )


class TestReadWindowAround:
    def test_window_shape_centered(self, default_ds: SyntheticDemDatasource) -> None:
        window = default_ds.read_window_around(GeoPoint(lat=18.5, lon=77.5), 2)
        assert window.elevation.shape == (5, 5)
        assert math.isfinite(window.center_value())

    def test_edge_window_padded_with_nan(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        # Point sits in cell (1, 1); radius 2 overhangs the north/west edge.
        window = default_ds.read_window_around(
            GeoPoint(lat=18.999, lon=77.001), 2
        )
        assert window.elevation.shape == (5, 5)
        assert np.isnan(window.elevation[0, :]).all()
        assert np.isnan(window.elevation[:, 0]).all()
        assert math.isfinite(window.center_value())

    def test_point_outside_extent_returns_nan_window(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        window = default_ds.read_window_around(
            GeoPoint(lat=17.5, lon=77.5), 1
        )
        assert window.elevation.shape == (3, 3)
        assert window.is_all_nodata()

    def test_max_edge_point_maps_inside(
        self, default_ds: SyntheticDemDatasource
    ) -> None:
        window = default_ds.read_window_around(
            GeoPoint(lat=19.0, lon=78.0), 0
        )
        # Corner cell (0, 1199): the hole does not reach it.
        assert math.isfinite(window.center_value())


class TestPing:
    def test_ping_true(self, default_ds: SyntheticDemDatasource) -> None:
        assert default_ds.ping() is True


class TestConstructor:
    def test_rejects_non_2d_elevation(
        self, mapper: DemWindowMapper
    ) -> None:
        extent = BoundingBox(min_lon=77.0, min_lat=18.0, max_lon=78.0, max_lat=19.0)
        with pytest.raises(DomainValidationError):
            SyntheticDemDatasource(
                np.zeros(10), extent, mapper, max_window_cells=100
            )
