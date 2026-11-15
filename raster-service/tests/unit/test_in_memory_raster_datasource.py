import numpy as np
import pytest

from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from tests.fixtures.make_test_raster import (
    TEST_BAND_NAMES,
    TEST_COLS,
    TEST_EXTENT,
    TEST_NODATA,
    TEST_ROWS,
    test_bands,
)


@pytest.fixture
def datasource(memory_datasource) -> InMemoryRasterDatasource:
    return memory_datasource


class TestConstruction:
    def test_rejects_non_3d_array(self):
        with pytest.raises(ValueError):
            InMemoryRasterDatasource(
                np.zeros((TEST_ROWS, TEST_COLS), dtype=np.float32), TEST_EXTENT
            )

    def test_rejects_description_count_mismatch(self):
        with pytest.raises(ValueError):
            InMemoryRasterDatasource(
                test_bands(), TEST_EXTENT, band_descriptions=("only_one",)
            )

    def test_defaults_descriptions_to_none(self):
        datasource = InMemoryRasterDatasource(test_bands(), TEST_EXTENT)

        assert datasource.read_metadata().band_descriptions == (None, None, None)


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


class TestReadCells:
    def test_full_band_values_are_verbatim(self, datasource):
        cells = datasource.read_cells(
            1, slice(0, TEST_ROWS), slice(0, TEST_COLS)
        )

        np.testing.assert_array_equal(cells, test_bands()[0])

    def test_window_reads_only_the_requested_cells(self, datasource):
        cells = datasource.read_cells(2, slice(2, 5), slice(1, 4))

        np.testing.assert_array_equal(cells, test_bands()[1, 2:5, 1:4])

    def test_band_index_out_of_range_raises(self, datasource):
        with pytest.raises(IndexError):
            datasource.read_cells(4, slice(0, 1), slice(0, 1))

        with pytest.raises(IndexError):
            datasource.read_cells(0, slice(0, 1), slice(0, 1))

    def test_read_cells_returns_a_copy(self, datasource):
        cells = datasource.read_cells(1, slice(0, 2), slice(0, 2))
        cells[0, 0] = -1.0

        fresh = datasource.read_cells(1, slice(0, 2), slice(0, 2))

        assert fresh[0, 0] == test_bands()[0, 0, 0]


class TestPing:
    def test_ping_true(self, datasource):
        assert datasource.ping() is True


class TestSynthetic:
    def test_synthetic_mimics_the_rejilla_grid(self):
        meta = InMemoryRasterDatasource.synthetic().read_metadata()

        assert (meta.rows, meta.cols) == (105, 72)
        assert meta.band_descriptions == (
            "pendiente_grados",
            "rugosidad_m",
            "fraccion_oscura",
            "inercia_termica_tiu",
            "albedo",
            "distancia_duna_m",
        )
        assert meta.is_geographic is True
        assert meta.is_north_up is True

    def test_synthetic_is_deterministic(self):
        first = InMemoryRasterDatasource.synthetic()
        second = InMemoryRasterDatasource.synthetic()

        assert first.read_metadata() == second.read_metadata()
        for band in (1, 3, 6):
            np.testing.assert_array_equal(
                first.read_cells(band, slice(0, 105), slice(0, 72)),
                second.read_cells(band, slice(0, 105), slice(0, 72)),
            )

    def test_synthetic_carries_a_nodata_cell(self):
        datasource = InMemoryRasterDatasource.synthetic()
        cells = datasource.read_cells(3, slice(0, 105), slice(0, 72))

        assert np.isnan(cells).sum() == 1
