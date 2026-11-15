from unittest.mock import Mock

import numpy as np
import pytest

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    NoCoverageError,
    RasterValidationError,
    UnknownBandError,
    UnknownDatasetError,
)
from app.features.window_read.application.read_window import ReadWindow
from app.features.window_read.domain.window_request import WindowRequest
from app.features.window_read.presentation.window_mapper import (
    WindowMapper,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource

# Test grid: extent lon 137.40..137.48 (8 cols), lat -4.70..-4.60
# (10 rows) of ~0.01 deg cells; row 0 is north. Band i (1-based) holds
# (i-1)*100 + row*10 + col. Band "slope_deg" cell (1, 1) is the numeric
# nodata sentinel; band "dark_fraction" cell (8, 6) is a real NaN.
BAND = "slope_deg"
MAX = 1_000_000


def _bbox_request(bbox, halo=0, band=BAND):
    return WindowRequest(
        band=band,
        bbox=BoundingBox(
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
        ),
        halo_cells=halo,
    )


def _point_request(lat, lon, radius, band=BAND, halo=0):
    return WindowRequest(
        band=band,
        point=GeoPoint(lat=lat, lon=lon),
        radius_cells=radius,
        halo_cells=halo,
    )


class TestWindowRequest:
    def test_bbox_only_is_valid(self):
        request = _bbox_request([137.41, -4.62, 137.43, -4.61])

        assert request.bbox is not None
        assert request.point is None

    def test_point_with_radius_is_valid(self):
        request = _point_request(-4.615, 137.415, 2)

        assert request.point is not None
        assert request.radius_cells == 2

    def test_both_bbox_and_point_rejected(self):
        with pytest.raises(RasterValidationError, match="exactly one"):
            WindowRequest(
                band=BAND,
                bbox=BoundingBox(
                    min_lon=137.41, min_lat=-4.62,
                    max_lon=137.43, max_lat=-4.61,
                ),
                point=GeoPoint(lat=-4.615, lon=137.415),
                radius_cells=1,
            )

    def test_neither_bbox_nor_point_rejected(self):
        with pytest.raises(RasterValidationError, match="exactly one"):
            WindowRequest(band=BAND)

    def test_point_without_radius_rejected(self):
        with pytest.raises(RasterValidationError, match="radius_cells"):
            WindowRequest(
                band=BAND, point=GeoPoint(lat=-4.615, lon=137.415)
            )

    def test_negative_radius_rejected(self):
        with pytest.raises(RasterValidationError, match="radius_cells"):
            _point_request(-4.615, 137.415, -1)

    def test_negative_halo_rejected(self):
        with pytest.raises(RasterValidationError, match="halo_cells"):
            _bbox_request([137.41, -4.62, 137.43, -4.61], halo=-1)

    def test_halo_ignored_and_normalised_on_point_reads(self):
        request = _point_request(-4.615, 137.415, 1, halo=7)

        assert request.halo_cells == 0

    def test_empty_band_rejected(self):
        with pytest.raises(RasterValidationError, match="band"):
            _bbox_request([137.41, -4.62, 137.43, -4.61], band="")


class TestReadWindowBbox:
    def test_selects_cells_whose_centres_fall_inside(self, repository):
        # Cell centres sit exactly on every edge of this bbox; the 1e-9
        # index epsilon keeps them inside (MS4 centre-inclusion rule).
        _, window, cells, center_lat = ReadWindow(repository, MAX).execute(
            "test", _bbox_request([137.415, -4.625, 137.435, -4.615])
        )

        assert (window.rows, window.cols) == (2, 3)
        assert (window.row_off, window.col_off) == (0, 0)
        assert (window.core_rows, window.core_cols) == (2, 3)
        np.testing.assert_array_equal(
            cells,
            np.array(
                [[np.nan, 12.0, 13.0], [21.0, 22.0, 23.0]]
            ),
        )
        assert center_lat == pytest.approx(-4.62)

    def test_values_are_verbatim_floats(self, repository):
        _, _, cells, _ = ReadWindow(repository, MAX).execute(
            "test", _bbox_request([137.415, -4.625, 137.435, -4.615])
        )

        assert type(cells[0, 1]) is np.float64
        assert float(cells[0, 1]) == 12.0

    def test_sub_cell_bbox_falls_back_to_single_cell(self, repository):
        # The bbox covers no cell centre -> the single cell containing
        # the intersection centre is returned (MS4 fallback rule).
        _, window, cells, _ = ReadWindow(repository, MAX).execute(
            "test", _bbox_request([137.406, -4.606, 137.408, -4.604])
        )

        assert (window.rows, window.cols) == (1, 1)
        np.testing.assert_array_equal(cells, np.array([[0.0]]))

    def test_halo_clipped_asymmetrically_at_grid_edge(self, repository):
        # Halo asks for 2 cells on every side; the north and west edges
        # clip to 1, and the core slice keeps the unexpanded range.
        _, window, cells, center_lat = ReadWindow(
            repository, MAX
        ).execute(
            "test",
            _bbox_request([137.415, -4.625, 137.435, -4.615], halo=2),
        )

        assert (window.rows, window.cols) == (5, 6)
        assert (window.row_off, window.col_off) == (1, 1)
        assert (window.core_rows, window.core_cols) == (2, 3)
        np.testing.assert_array_equal(
            cells,
            np.array(
                [
                    [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
                    [10.0, np.nan, 12.0, 13.0, 14.0, 15.0],
                    [20.0, 21.0, 22.0, 23.0, 24.0, 25.0],
                    [30.0, 31.0, 32.0, 33.0, 34.0, 35.0],
                    [40.0, 41.0, 42.0, 43.0, 44.0, 45.0],
                ]
            ),
        )
        # center_lat uses the core rows even under asymmetric clipping.
        assert center_lat == pytest.approx(-4.62)

    def test_non_intersecting_bbox_raises_no_coverage(self, repository):
        with pytest.raises(NoCoverageError):
            ReadWindow(repository, MAX).execute(
                "test", _bbox_request([140.0, 10.0, 141.0, 11.0])
            )

    def test_core_cells_over_cap_raises_before_read(
        self, repository, monkeypatch
    ):
        read = Mock(wraps=repository.read_cells)
        monkeypatch.setattr(repository, "read_cells", read)

        with pytest.raises(RasterValidationError, match="limit"):
            ReadWindow(repository, max_window_cells=10).execute(
                "test",
                _bbox_request([137.40, -4.70, 137.48, -4.60]),  # 80 cells
            )
        read.assert_not_called()

    def test_unknown_band_raises_listing_valid_names(self, repository):
        with pytest.raises(UnknownBandError) as excinfo:
            ReadWindow(repository, MAX).execute(
                "test",
                _bbox_request(
                    [137.41, -4.62, 137.43, -4.61], band="nope"
                ),
            )

        assert "slope_deg" in str(excinfo.value)

    def test_unknown_dataset_raises(self, repository):
        with pytest.raises(UnknownDatasetError):
            ReadWindow(repository, MAX).execute(
                "nope", _bbox_request([137.41, -4.62, 137.43, -4.61])
            )

    def test_unavailable_dataset_raises(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(DatasetUnavailableError):
            ReadWindow(repository, MAX).execute(
                "broken", _bbox_request([137.41, -4.62, 137.43, -4.61])
            )


class TestReadWindowPoint:
    def test_radius_zero_returns_containing_cell(self, repository):
        _, window, cells, center_lat = ReadWindow(repository, MAX).execute(
            "test", _point_request(-4.625, 137.425, 0)
        )

        assert (window.rows, window.cols) == (1, 1)
        np.testing.assert_array_equal(cells, np.array([[22.0]]))
        assert center_lat == pytest.approx(-4.625)

    def test_radius_one_returns_3x3_around_cell(self, repository):
        _, window, cells, center_lat = ReadWindow(repository, MAX).execute(
            "test", _point_request(-4.625, 137.425, 1)
        )

        assert (window.rows, window.cols) == (3, 3)
        assert (window.row_off, window.col_off) == (0, 0)
        np.testing.assert_array_equal(
            cells,
            np.array(
                [
                    [np.nan, 12.0, 13.0],
                    [21.0, 22.0, 23.0],
                    [31.0, 32.0, 33.0],
                ]
            ),
        )
        assert center_lat == pytest.approx(-4.625)

    def test_edge_window_padded_with_nan(self, repository):
        # Ported MS4 case: point sits in cell (1, 1); radius 2 overhangs
        # the north/west edge -> top row and left column are NaN padding.
        _, _, cells, _ = ReadWindow(repository, MAX).execute(
            "test",
            _point_request(-4.615, 137.415, 2, band="roughness_m"),
        )

        assert cells.shape == (5, 5)
        assert np.isnan(cells[0, :]).all()
        assert np.isnan(cells[:, 0]).all()
        assert cells[2, 2] == 111.0

    def test_point_on_max_edge_maps_inside(self, repository):
        # Ported MS4 case: a point exactly on the north/east corner
        # clamps into the boundary cell (0, 7).
        _, _, cells, center_lat = ReadWindow(repository, MAX).execute(
            "test", _point_request(-4.60, 137.48, 0)
        )

        np.testing.assert_array_equal(cells, np.array([[7.0]]))
        assert center_lat == pytest.approx(-4.605)

    def test_point_outside_extent_returns_all_nan_window(
        self, repository, monkeypatch
    ):
        # Ported MS4 case: never NoCoverageError; a (2r+1)^2 all-NaN
        # window with center_lat = the request latitude, without any read.
        read = Mock(wraps=repository.read_cells)
        monkeypatch.setattr(repository, "read_cells", read)

        _, window, cells, center_lat = ReadWindow(repository, MAX).execute(
            "test", _point_request(-4.55, 137.44, 1)
        )

        assert cells.shape == (3, 3)
        assert np.isnan(cells).all()
        assert (window.rows, window.cols) == (3, 3)
        assert center_lat == -4.55
        read.assert_not_called()

    def test_point_radius_cap_raises_before_read(
        self, repository, monkeypatch
    ):
        read = Mock(wraps=repository.read_cells)
        monkeypatch.setattr(repository, "read_cells", read)

        with pytest.raises(RasterValidationError, match="limit"):
            # radius 3 -> 7x7 = 49 cells > 10
            ReadWindow(repository, max_window_cells=10).execute(
                "test", _point_request(-4.65, 137.44, 3)
            )
        read.assert_not_called()

    def test_halo_cells_ignored_on_point_reads(self, repository):
        _, with_halo, cells_with_halo, _ = ReadWindow(
            repository, MAX
        ).execute("test", _point_request(-4.625, 137.425, 1, halo=3))
        _, plain, cells_plain, _ = ReadWindow(repository, MAX).execute(
            "test", _point_request(-4.625, 137.425, 1)
        )

        assert (with_halo.rows, with_halo.cols) == (3, 3)
        np.testing.assert_array_equal(cells_with_halo, cells_plain)


class TestWindowMapper:
    def test_non_finite_cells_serialize_as_null(self, repository):
        # NaN and +-inf all become null on the wire (D5).
        metadata, window, _, center_lat = ReadWindow(
            repository, MAX
        ).execute("test", _bbox_request([137.41, -4.62, 137.43, -4.61]))

        response = WindowMapper.to_response(
            "slope_deg",
            metadata,
            window,
            np.array([[np.nan, np.inf, -np.inf]]),
            center_lat,
        )

        assert response.cells == [[None, None, None]]
