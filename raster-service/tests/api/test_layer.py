import struct
import zlib

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config.dataset_config import DatasetConfig
from app.features.layer_render.presentation.layer_router import router
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.conftest import TEST_DATASET, mount_router
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
from tests.fixtures.make_test_raster import TEST_EXTENT

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8 cols.
# Band "slope_deg" holds row*10 + col (nodata at (1, 1)), configured
# colormap "slope", configured range (0, 35).


@pytest.fixture
def client(api_repository, api_settings) -> TestClient:
    return mount_router(router, api_repository, api_settings)


def _decode_png(png: bytes) -> np.ndarray:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    width = height = None
    idat = b""
    while pos < len(png):
        length = struct.unpack(">I", png[pos : pos + 4])[0]
        kind = png[pos + 4 : pos + 8]
        data = png[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height = struct.unpack(">II", data[:8])
        elif kind == b"IDAT":
            idat += data
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * 4
    pixels = np.empty((height, stride), dtype=np.uint8)
    for row in range(height):
        base = row * (stride + 1)
        assert raw[base] == 0
        pixels[row] = np.frombuffer(
            raw[base + 1 : base + 1 + stride], dtype=np.uint8
        )
    return pixels.reshape(height, width, 4)


def _single_band_client(cells: np.ndarray) -> TestClient:
    datasource = InMemoryRasterDatasource(
        np.asarray(cells, dtype=np.float64)[np.newaxis, :, :],
        TEST_EXTENT,
        band_descriptions=("band1",),
        nodata=None,
    )
    repository = RegistryRasterRepository(
        datasources={TEST_DATASET: datasource},
        configs={TEST_DATASET: DatasetConfig(path="")},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )
    return mount_router(router, repository)


class TestLayer:
    def test_returns_png_with_georeferencing_headers(self, client):
        response = client.get("/raster/test/layer/slope_deg")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        bounds = [
            float(v)
            for v in response.headers["x-raster-bounds"].split(",")
        ]
        assert bounds == pytest.approx(
            [
                TEST_EXTENT.min_lon,
                TEST_EXTENT.min_lat,
                TEST_EXTENT.max_lon,
                TEST_EXTENT.max_lat,
            ]
        )
        assert response.headers["x-raster-crs"] == "IAU_2015:49900"
        value_range = [
            float(v)
            for v in response.headers["x-raster-value-range"].split(",")
        ]
        assert value_range == [0.0, 35.0]

    def test_body_is_valid_png_one_pixel_per_cell(self, client):
        response = client.get("/raster/test/layer/slope_deg")

        image = _decode_png(response.content)
        assert image.shape == (10, 8, 4)
        assert tuple(image[0, 0]) == (0, 128, 0, 255)
        # nodata cell (1, 1) is fully transparent
        assert tuple(image[1, 1]) == (0, 0, 0, 0)

    def test_colormap_query_overrides_band_default(self, client):
        response = client.get(
            "/raster/test/layer/slope_deg", params={"colormap": "grayscale"}
        )

        assert response.status_code == 200
        image = _decode_png(response.content)
        assert tuple(image[0, 0]) == (0, 0, 0, 255)

    def test_unknown_colormap_is_400(self, client):
        response = client.get(
            "/raster/test/layer/slope_deg", params={"colormap": "nope"}
        )

        assert response.status_code == 400
        assert "nope" in response.json()["detail"]

    def test_unknown_band_is_404_and_lists_valid_names(self, client):
        response = client.get("/raster/test/layer/nope")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "nope" in detail
        assert "slope_deg" in detail

    def test_unknown_dataset_is_404(self, client):
        response = client.get("/raster/nope/layer/slope_deg")

        assert response.status_code == 404

    def test_unreadable_dataset_is_503(self, api_dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": api_dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )
        client = mount_router(router, repository)

        response = client.get("/raster/broken/layer/slope_deg")

        assert response.status_code == 503

    def test_all_nan_band_is_fully_transparent_png(self):
        client = _single_band_client(np.full((10, 8), np.nan))

        response = client.get("/raster/test/layer/band1")

        assert response.status_code == 200
        assert (_decode_png(response.content) == 0).all()
        assert response.headers["x-raster-value-range"] == "0.0,1.0"

    def test_constant_band_renders_mid_ramp_colour(self):
        client = _single_band_client(np.full((10, 8), 7.0))

        response = client.get("/raster/test/layer/band1")

        assert response.status_code == 200
        image = _decode_png(response.content)
        assert (image == (33, 145, 140, 255)).all(axis=-1).all()
        assert response.headers["x-raster-value-range"] == "7.0,7.0"
