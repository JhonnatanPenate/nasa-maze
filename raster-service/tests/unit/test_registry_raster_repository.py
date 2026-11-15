import logging
import math

import numpy as np
import pytest

from app.core.config.dataset_config import DatasetConfig
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    RasterValidationError,
    UnknownBandError,
    UnknownDatasetError,
)
from app.core.ports.raster_datasource import RasterDatasource
from app.infrastructure.datasources.geotiff_raster_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.datasources.unavailable_raster_datasource import (
    UnavailableRasterDatasource,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.conftest import TEST_BAND_UNITS, TEST_DATASET
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
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
    write_test_raster_nan_nodata,
    write_test_raster_projected,
    write_test_raster_rotated,
)


def _repo_for(datasource, config: DatasetConfig | None = None):
    return RegistryRasterRepository(
        datasources={TEST_DATASET: datasource},
        configs={TEST_DATASET: config or DatasetConfig(path="")},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )


class _CountingDatasource(RasterDatasource):
    """Counts read_metadata calls to prove the repository caches metadata."""

    def __init__(self, inner: RasterDatasource) -> None:
        self._inner = inner
        self.metadata_calls = 0

    def read_metadata(self):
        self.metadata_calls += 1
        return self._inner.read_metadata()

    def read_cells(self, band_index, rows, cols):
        return self._inner.read_cells(band_index, rows, cols)

    def ping(self):
        return self._inner.ping()


class TestSwapSuite:
    """Runs against InMemoryRasterDatasource AND GeoTiffRasterDatasource
    via the parametrized `repository` fixture — the datasource swap proof."""

    def test_dataset_names(self, repository):
        assert repository.dataset_names() == [TEST_DATASET]

    def test_metadata_shape_crs_and_resolution(self, repository):
        meta = repository.metadata(TEST_DATASET)

        assert meta.name == TEST_DATASET
        assert meta.crs == "IAU_2015:49900"
        assert meta.bounds == TEST_EXTENT
        assert meta.width == TEST_COLS
        assert meta.height == TEST_ROWS
        assert meta.res_lon_deg == pytest.approx(0.01)
        assert meta.res_lat_deg == pytest.approx(0.01)
        expected_m = 0.01 * math.pi / 180.0 * 3396190.0
        assert meta.resolution_m == pytest.approx(expected_m)

    def test_metadata_band_names_and_units(self, repository):
        meta = repository.metadata(TEST_DATASET)

        assert meta.band_names() == list(TEST_BAND_NAMES)
        for band, name in zip(meta.bands, TEST_BAND_NAMES):
            assert band.unit == TEST_BAND_UNITS[name]
            assert band.nodata == TEST_NODATA

    def test_metadata_merges_render_config(self, repository):
        meta = repository.metadata(TEST_DATASET)

        assert meta.band("slope_deg").colormap == "slope"
        assert meta.band("slope_deg").value_range == (0.0, 35.0)
        assert meta.band("roughness_m").colormap == "viridis"
        assert meta.band("roughness_m").value_range is None

    def test_read_cells_returns_float64_verbatim_values(self, repository):
        cells = repository.read_cells(
            TEST_DATASET, "roughness_m", slice(2, 5), slice(1, 4)
        )

        assert cells.dtype == np.float64
        np.testing.assert_array_equal(
            cells, test_bands()[1, 2:5, 1:4].astype(np.float64)
        )

    def test_read_cells_maps_numeric_nodata_to_nan(self, repository):
        row, col = TEST_NODATA_CELL
        cells = repository.read_cells(
            TEST_DATASET, "slope_deg", slice(row, row + 1), slice(col, col + 1)
        )

        assert np.isnan(cells[0, 0])

    def test_read_cells_keeps_nan_cells_nan(self, repository):
        row, col = TEST_NAN_CELL
        cells = repository.read_cells(
            TEST_DATASET,
            "dark_fraction",
            slice(row, row + 1),
            slice(col, col + 1),
        )

        assert np.isnan(cells[0, 0])

    def test_unknown_dataset(self, repository):
        with pytest.raises(UnknownDatasetError, match="test"):
            repository.metadata("nope")
        with pytest.raises(UnknownDatasetError):
            repository.read_cells(
                "nope", "slope_deg", slice(0, 1), slice(0, 1)
            )
        assert repository.is_readable("nope") is False

    def test_unknown_band_lists_valid_names(self, repository):
        with pytest.raises(UnknownBandError, match="slope_deg"):
            repository.read_cells(
                TEST_DATASET, "nope", slice(0, 1), slice(0, 1)
            )

    def test_metadata_is_cached(self, datasource):
        counting = _CountingDatasource(datasource)
        repo = _repo_for(counting)

        repo.metadata(TEST_DATASET)
        repo.metadata(TEST_DATASET)
        repo.read_cells(
            TEST_DATASET, "slope_deg", slice(0, 2), slice(0, 2)
        )

        assert counting.metadata_calls == 1


class TestSliceNormalisation:
    """Parametrized over `datasource` — both implementations must accept
    and normalise the same slice forms."""

    def test_slice_none_reads_the_full_band(self, datasource):
        cells = datasource.read_cells(1, slice(None), slice(None))

        np.testing.assert_array_equal(cells, test_bands()[0])

    def test_negative_offsets_normalise(self, datasource):
        cells = datasource.read_cells(1, slice(-2, None), slice(None))

        np.testing.assert_array_equal(cells, test_bands()[0, -2:, :])

    def test_stepped_slice_is_rejected(self, datasource):
        with pytest.raises(ValueError):
            datasource.read_cells(1, slice(0, 4, 2), slice(None))


class TestErrorMapping:
    def test_failing_datasource_maps_to_unavailable(self, dataset_config):
        repo = _repo_for(FailingRasterDatasource(), dataset_config)

        with pytest.raises(DatasetUnavailableError) as excinfo:
            repo.metadata(TEST_DATASET)
        assert str(excinfo.value) == "Dataset 'test' is unavailable"
        with pytest.raises(DatasetUnavailableError) as excinfo:
            repo.read_cells(
                TEST_DATASET, "slope_deg", slice(0, 1), slice(0, 1)
            )
        assert str(excinfo.value) == "Dataset 'test' is unavailable"
        assert repo.is_readable(TEST_DATASET) is False

    def test_original_error_is_logged_not_leaked(
        self, dataset_config, caplog
    ):
        repo = _repo_for(FailingRasterDatasource(), dataset_config)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(DatasetUnavailableError) as excinfo:
                repo.metadata(TEST_DATASET)

        assert "read_metadata unavailable" in caplog.text
        assert "read_metadata unavailable" not in str(excinfo.value)

    def test_read_cells_failure_wraps_after_cached_metadata(
        self, memory_datasource, dataset_config
    ):
        class HalfBroken(FailingRasterDatasource):
            def read_metadata(self):
                return memory_datasource.read_metadata()

            def ping(self):
                return True

        repo = _repo_for(HalfBroken(), dataset_config)
        repo.metadata(TEST_DATASET)

        with pytest.raises(DatasetUnavailableError):
            repo.read_cells(
                TEST_DATASET, "slope_deg", slice(0, 1), slice(0, 1)
            )

    def test_unavailable_datasource(self, dataset_config):
        repo = _repo_for(
            UnavailableRasterDatasource(RuntimeError("build failed")),
            dataset_config,
        )

        with pytest.raises(DatasetUnavailableError):
            repo.metadata(TEST_DATASET)
        assert repo.is_readable(TEST_DATASET) is False

    def test_non_geographic_dataset_is_unavailable(self, tmp_path):
        path = write_test_raster_projected(tmp_path / "projected.tif")
        repo = _repo_for(GeoTiffRasterDatasource(path))

        with pytest.raises(DatasetUnavailableError, match="geographic"):
            repo.metadata(TEST_DATASET)
        assert repo.is_readable(TEST_DATASET) is False

    def test_rotated_dataset_is_unavailable(self, tmp_path):
        path = write_test_raster_rotated(tmp_path / "rotated.tif")
        repo = _repo_for(GeoTiffRasterDatasource(path))

        with pytest.raises(DatasetUnavailableError, match="north-up"):
            repo.metadata(TEST_DATASET)
        assert repo.is_readable(TEST_DATASET) is False

    def test_is_readable_false_when_ping_ok_but_metadata_fails(
        self, dataset_config
    ):
        class PingOkButBroken(FailingRasterDatasource):
            def ping(self):
                return True

        repo = _repo_for(PingOkButBroken(), dataset_config)

        assert repo.is_readable(TEST_DATASET) is False

    def test_is_readable_false_when_metadata_is_invalid(
        self, dataset_config
    ):
        datasource = InMemoryRasterDatasource(
            test_bands(),
            TEST_EXTENT,
            band_descriptions=("dup", "dup", "dup"),
            nodata=TEST_NODATA,
        )
        repo = _repo_for(datasource, dataset_config)

        with pytest.raises(RasterValidationError):
            repo.metadata(TEST_DATASET)
        assert repo.is_readable(TEST_DATASET) is False

    def test_missing_config_entry_uses_empty_defaults(
        self, memory_datasource
    ):
        repo = RegistryRasterRepository(
            datasources={TEST_DATASET: memory_datasource},
            configs={},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        meta = repo.metadata(TEST_DATASET)

        for band in meta.bands:
            assert band.unit == ""
            assert band.colormap == "viridis"  # DatasetConfig default
            assert band.value_range is None


class TestBandNameFallback:
    def test_config_band_names_used_when_descriptions_empty(self):
        datasource = InMemoryRasterDatasource(
            test_bands(), TEST_EXTENT, nodata=TEST_NODATA
        )
        config = DatasetConfig(path="", band_names=["a", "b", "c"])
        repo = _repo_for(datasource, config)

        assert repo.metadata(TEST_DATASET).band_names() == ["a", "b", "c"]

    def test_band_i_used_when_no_descriptions_or_config_names(self):
        datasource = InMemoryRasterDatasource(
            test_bands(), TEST_EXTENT, nodata=TEST_NODATA
        )
        repo = _repo_for(datasource, DatasetConfig(path="", band_names=[]))

        assert repo.metadata(TEST_DATASET).band_names() == [
            "band_1",
            "band_2",
            "band_3",
        ]


class TestNaNMetadataSentinel:
    def test_nan_sentinel_reports_null_nodata(self):
        datasource = InMemoryRasterDatasource(
            test_bands(), TEST_EXTENT, nodata=float("nan")
        )
        meta = _repo_for(datasource).metadata(TEST_DATASET)

        assert all(band.nodata is None for band in meta.bands)

    def test_nan_nodata_geotiff_reports_null_and_serves_nan(
        self, tmp_path
    ):
        path = write_test_raster_nan_nodata(tmp_path / "nan_nodata.tif")
        repo = _repo_for(GeoTiffRasterDatasource(path))

        meta = repo.metadata(TEST_DATASET)
        assert all(band.nodata is None for band in meta.bands)

        row, col = TEST_NAN_CELL
        cells = repo.read_cells(
            TEST_DATASET,
            "dark_fraction",
            slice(row, row + 1),
            slice(col, col + 1),
        )
        assert np.isnan(cells[0, 0])
