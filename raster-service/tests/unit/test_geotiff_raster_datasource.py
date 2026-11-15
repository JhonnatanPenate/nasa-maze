import math

import numpy as np
import pytest
import rasterio

from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from tests.fixtures.make_test_raster import (
    TEST_BAND_NAMES,
    TEST_COLS,
    TEST_EXTENT,
    TEST_NAN_BAND,
    TEST_NAN_CELL,
    TEST_NODATA,
    TEST_NODATA_BAND,
    TEST_NODATA_CELL,
    TEST_ROWS,
    test_bands,
    write_test_raster,
    write_test_raster_nan_nodata,
    write_test_raster_projected,
    write_test_raster_rotated,
)


@pytest.fixture
def raster_path(tmp_path):
    return write_test_raster(tmp_path / "grid.tif")


@pytest.fixture
def datasource(raster_path) -> GeoTiffRasterDatasource:
    return GeoTiffRasterDatasource(raster_path)


class TestReadMetadata:
    def test_reports_extent_shape_descriptions_and_nodata(self, datasource):
        meta = datasource.read_metadata()

        assert meta.extent == TEST_EXTENT
        assert meta.rows == TEST_ROWS
        assert meta.cols == TEST_COLS
        assert meta.band_descriptions == TEST_BAND_NAMES
        assert meta.nodata == TEST_NODATA
        assert meta.is_geographic is True
        assert meta.is_north_up is True

    def test_missing_file_raises(self, tmp_path):
        datasource = GeoTiffRasterDatasource(tmp_path / "absent.tif")

        with pytest.raises(rasterio.errors.RasterioIOError):
            datasource.read_metadata()

    def test_projected_raster_is_not_geographic(self, tmp_path):
        path = write_test_raster_projected(tmp_path / "projected.tif")
        meta = GeoTiffRasterDatasource(path).read_metadata()

        assert meta.is_geographic is False
        assert meta.is_north_up is True

    def test_rotated_raster_is_not_north_up(self, tmp_path):
        path = write_test_raster_rotated(tmp_path / "rotated.tif")
        meta = GeoTiffRasterDatasource(path).read_metadata()

        assert meta.is_geographic is True
        assert meta.is_north_up is False

    def test_nan_nodata_file_reports_nan_sentinel(self, tmp_path):
        path = write_test_raster_nan_nodata(tmp_path / "nan_nodata.tif")
        meta = GeoTiffRasterDatasource(path).read_metadata()

        assert math.isnan(meta.nodata)


class TestReadCells:
    def test_full_band_values_are_verbatim_float32(self, datasource):
        cells = datasource.read_cells(
            1, slice(0, TEST_ROWS), slice(0, TEST_COLS)
        )

        assert cells.dtype == np.float32
        np.testing.assert_array_equal(cells, test_bands()[0])

    def test_window_reads_only_the_requested_cells(self, datasource):
        cells = datasource.read_cells(2, slice(2, 5), slice(1, 4))

        np.testing.assert_array_equal(cells, test_bands()[1, 2:5, 1:4])

    def test_single_cell_window(self, datasource):
        cells = datasource.read_cells(3, slice(4, 5), slice(7, 8))

        assert cells.shape == (1, 1)
        assert cells[0, 0] == test_bands()[2, 4, 7]

    def test_numeric_nodata_cell_is_served_verbatim(self, datasource):
        cells = datasource.read_cells(
            TEST_NODATA_BAND,
            slice(TEST_NODATA_CELL[0], TEST_NODATA_CELL[0] + 1),
            slice(TEST_NODATA_CELL[1], TEST_NODATA_CELL[1] + 1),
        )

        assert cells[0, 0] == TEST_NODATA

    def test_nan_cell_is_served_verbatim(self, datasource):
        cells = datasource.read_cells(
            TEST_NAN_BAND,
            slice(TEST_NAN_CELL[0], TEST_NAN_CELL[0] + 1),
            slice(TEST_NAN_CELL[1], TEST_NAN_CELL[1] + 1),
        )

        assert np.isnan(cells[0, 0])

    def test_unknown_band_index_raises(self, datasource):
        with pytest.raises(Exception):
            datasource.read_cells(4, slice(0, 1), slice(0, 1))


class TestPing:
    def test_ping_true_for_readable_file(self, datasource):
        assert datasource.ping() is True

    def test_ping_false_for_missing_file(self, tmp_path):
        datasource = GeoTiffRasterDatasource(tmp_path / "absent.tif")

        assert datasource.ping() is False

    def test_ping_false_for_projected_raster(self, tmp_path):
        path = write_test_raster_projected(tmp_path / "projected.tif")

        assert GeoTiffRasterDatasource(path).ping() is False
