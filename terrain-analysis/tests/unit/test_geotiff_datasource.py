from unittest.mock import Mock

import numpy as np
import pytest
import rasterio
from affine import Affine

from app.core.domain.bounding_box import BoundingBox
from app.core.domain.geo_point import GeoPoint
from app.core.errors.exceptions import (
    DomainValidationError,
    UpstreamDatasourceError,
)
from app.infrastructure.datasources.dem_window_mapper import DemWindowMapper
from app.infrastructure.datasources.geotiff_datasource import (
    GeoTiffRasterDatasource,
)
from app.infrastructure.repositories.dem_terrain_repository import (
    DemTerrainRepository,
)
from tests.conftest import TEST_NODATA

CELL_DEG = 0.2 / 21.0
FULL_BBOX = BoundingBox(min_lon=77.4, min_lat=18.4, max_lon=77.6, max_lat=18.6)


def _write_geotiff(
    path, elevation: np.ndarray, transform: Affine, crs, nodata=-32768.0
) -> None:
    elevation = np.asarray(elevation, dtype=np.float32)
    rows, cols = elevation.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=rows,
        width=cols,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(elevation, 1)


@pytest.fixture
def mapper() -> DemWindowMapper:
    return DemWindowMapper(3_389_500.0)


@pytest.fixture
def geo_ds(geotiff_path, mapper) -> GeoTiffRasterDatasource:
    return GeoTiffRasterDatasource(str(geotiff_path), mapper, 4_000_000)


class TestReads:
    def test_read_window_returns_values(
        self, geo_ds: GeoTiffRasterDatasource
    ) -> None:
        window = geo_ds.read_window(
            BoundingBox(
                min_lon=77.49, min_lat=18.49, max_lon=77.51, max_lat=18.51
            )
        )
        assert window.elevation.shape == (3, 3)
        np.testing.assert_array_equal(
            window.elevation,
            np.array(
                [
                    [491.0, 493.0, 495.0],
                    [488.0, 490.0, 492.0],
                    [485.0, 487.0, 489.0],
                ]
            ),
        )

    def test_read_window_around_point(
        self, geo_ds: GeoTiffRasterDatasource
    ) -> None:
        window = geo_ds.read_window_around(GeoPoint(lat=18.5, lon=77.5), 0)
        assert window.elevation.shape == (1, 1)
        assert window.center_value() == 490.0

    def test_nodata_cell_reads_as_nan(
        self, geo_ds: GeoTiffRasterDatasource
    ) -> None:
        point = GeoPoint(
            lat=18.6 - 5.5 * CELL_DEG, lon=77.4 + 5.5 * CELL_DEG
        )
        window = geo_ds.read_window_around(point, 0)
        assert np.isnan(window.center_value())


class TestPing:
    def test_ping_true(self, geo_ds: GeoTiffRasterDatasource) -> None:
        assert geo_ds.ping() is True

    def test_ping_false_missing_file(
        self, tmp_path, mapper: DemWindowMapper
    ) -> None:
        ds = GeoTiffRasterDatasource(
            str(tmp_path / "does_not_exist.tif"), mapper, 4_000_000
        )
        assert ds.ping() is False

    def test_ping_false_corrupt_file(
        self, tmp_path, mapper: DemWindowMapper
    ) -> None:
        path = tmp_path / "corrupt.tif"
        path.write_bytes(b"this is not a TIFF file")
        ds = GeoTiffRasterDatasource(str(path), mapper, 4_000_000)
        assert ds.ping() is False


class TestRepositoryWrapping:
    def test_missing_file_upstream_error(
        self, tmp_path, mapper: DemWindowMapper
    ) -> None:
        repo = DemTerrainRepository(
            GeoTiffRasterDatasource(
                str(tmp_path / "missing.tif"), mapper, 4_000_000
            )
        )
        with pytest.raises(UpstreamDatasourceError):
            repo.elevation_at(GeoPoint(lat=18.5, lon=77.5))

    def test_corrupt_file_upstream_error(
        self, tmp_path, mapper: DemWindowMapper
    ) -> None:
        path = tmp_path / "corrupt.tif"
        path.write_bytes(b"not a TIFF")
        repo = DemTerrainRepository(
            GeoTiffRasterDatasource(str(path), mapper, 4_000_000)
        )
        with pytest.raises(UpstreamDatasourceError):
            repo.window_for(FULL_BBOX)


class TestDatasetValidation:
    def test_south_up_raster_rejected(
        self, tmp_path, mapper: DemWindowMapper, small_dem
    ) -> None:
        elevation, extent = small_dem
        path = tmp_path / "south_up.tif"
        south_up = Affine(0.01, 0.0, 77.4, 0.0, 0.01, 18.4)  # e > 0
        _write_geotiff(path, elevation, south_up, "EPSG:4326")
        ds = GeoTiffRasterDatasource(str(path), mapper, 4_000_000)
        with pytest.raises(UpstreamDatasourceError, match="north-up"):
            ds.read_window(FULL_BBOX)
        assert ds.ping() is False

    def test_projected_crs_rejected(
        self, tmp_path, mapper: DemWindowMapper, small_dem
    ) -> None:
        elevation, _ = small_dem
        path = tmp_path / "projected.tif"
        metric = Affine(30.0, 0.0, 500_000.0, 0.0, -30.0, 0.0)
        _write_geotiff(path, elevation, metric, "EPSG:32633")
        ds = GeoTiffRasterDatasource(str(path), mapper, 4_000_000)
        with pytest.raises(UpstreamDatasourceError, match="geographic"):
            ds.read_window(FULL_BBOX)
        assert ds.ping() is False


class TestLimits:
    def test_max_window_cells_raises_before_read(
        self, geotiff_path, mapper: DemWindowMapper, monkeypatch
    ) -> None:
        ds = GeoTiffRasterDatasource(str(geotiff_path), mapper, 10)
        read = Mock(wraps=ds._read)
        monkeypatch.setattr(ds, "_read", read)
        with pytest.raises(DomainValidationError):
            ds.read_window(FULL_BBOX)  # 441 cells > 10
        read.assert_not_called()

    def test_window_around_radius_cap(
        self, geotiff_path, mapper: DemWindowMapper, monkeypatch
    ) -> None:
        ds = GeoTiffRasterDatasource(str(geotiff_path), mapper, 10)
        read = Mock(wraps=ds._read)
        monkeypatch.setattr(ds, "_read", read)
        with pytest.raises(DomainValidationError):
            # radius 3 -> 7x7 = 49 cells > 10
            ds.read_window_around(GeoPoint(lat=18.5, lon=77.5), 3)
        read.assert_not_called()
