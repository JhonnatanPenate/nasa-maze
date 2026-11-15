import struct
import zlib

import numpy as np
import pytest

from app.core.config.dataset_config import DatasetConfig
from app.core.errors.exceptions import (
    DatasetUnavailableError,
    RasterValidationError,
    UnknownBandError,
    UnknownDatasetError,
)
from app.features.layer_render.application.render_layer import RenderLayer
from app.infrastructure.datasources.in_memory_raster_datasource import (
    InMemoryRasterDatasource,
)
from app.infrastructure.rendering.png_encoder import PngEncoder
from app.infrastructure.repositories.registry_raster_repository import (
    RegistryRasterRepository,
)
from tests.fakes.failing_raster_datasource import FailingRasterDatasource
from tests.fixtures.make_test_raster import TEST_EXTENT

# Test grid: extent lon 137.40..137.48, lat -4.70..-4.60, 10 rows x 8 cols.
# Band i (1-based) holds (i-1)*100 + row*10 + col; band 1 ("slope_deg")
# has a nodata cell at (1, 1) and configured colormap "slope" / range
# (0, 35); band 3 ("dark_fraction") has a NaN cell at (8, 6).


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


def _single_band_repository(cells: np.ndarray) -> RegistryRasterRepository:
    datasource = InMemoryRasterDatasource(
        np.asarray(cells, dtype=np.float64)[np.newaxis, :, :],
        TEST_EXTENT,
        band_descriptions=("band1",),
        nodata=None,
    )
    return RegistryRasterRepository(
        datasources={"test": datasource},
        configs={"test": DatasetConfig(path="")},
        crs_label="IAU_2015:49900",
        planet_radius_km=3396.19,
    )


class TestRenderLayer:
    def test_renders_png_with_bounds_crs_and_configured_range(
        self, repository
    ):
        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "slope_deg"
        )

        assert layer.png.startswith(b"\x89PNG\r\n\x1a\n")
        assert layer.bounds == TEST_EXTENT
        assert layer.crs == "IAU_2015:49900"
        assert layer.value_range == (0.0, 35.0)

    def test_image_is_one_pixel_per_cell_row_zero_north(self, repository):
        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "slope_deg"
        )

        image = _decode_png(layer.png)
        assert image.shape == (10, 8, 4)
        # slope_deg cell (0, 0) = 0.0 -> first "slope" stop (green)
        assert tuple(image[0, 0]) == (0, 128, 0, 255)

    def test_nodata_cell_is_transparent(self, repository):
        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "slope_deg"
        )

        image = _decode_png(layer.png)
        assert tuple(image[1, 1]) == (0, 0, 0, 0)

    def test_colormap_argument_overrides_band_default(self, repository):
        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "slope_deg", colormap="grayscale"
        )

        image = _decode_png(layer.png)
        # value 0 -> bottom of grayscale ramp (black), not slope green
        assert tuple(image[0, 0]) == (0, 0, 0, 255)

    def test_range_falls_back_to_finite_min_max(self, repository):
        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "roughness_m"
        )

        assert layer.value_range == (100.0, 197.0)
        image = _decode_png(layer.png)
        # default colormap viridis: min value -> first stop
        assert tuple(image[0, 0]) == (68, 1, 84, 255)

    def test_unknown_colormap_raises_validation(self, repository):
        with pytest.raises(RasterValidationError):
            RenderLayer(repository, PngEncoder()).execute(
                "test", "slope_deg", colormap="nope"
            )

    def test_unknown_band_raises(self, repository):
        with pytest.raises(UnknownBandError):
            RenderLayer(repository, PngEncoder()).execute("test", "nope")

    def test_unknown_dataset_raises(self, repository):
        with pytest.raises(UnknownDatasetError):
            RenderLayer(repository, PngEncoder()).execute(
                "nope", "slope_deg"
            )

    def test_unavailable_dataset_raises(self, dataset_config):
        repository = RegistryRasterRepository(
            datasources={"broken": FailingRasterDatasource()},
            configs={"broken": dataset_config},
            crs_label="IAU_2015:49900",
            planet_radius_km=3396.19,
        )

        with pytest.raises(DatasetUnavailableError):
            RenderLayer(repository, PngEncoder()).execute(
                "broken", "slope_deg"
            )

    def test_all_nan_band_is_fully_transparent(self):
        repository = _single_band_repository(np.full((10, 8), np.nan))

        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "band1"
        )

        image = _decode_png(layer.png)
        assert (image == 0).all()
        # defined fallback range for legend purposes
        assert layer.value_range == (0.0, 1.0)

    def test_constant_band_renders_mid_ramp_colour(self):
        repository = _single_band_repository(np.full((10, 8), 7.0))

        layer = RenderLayer(repository, PngEncoder()).execute(
            "test", "band1"
        )

        assert layer.value_range == (7.0, 7.0)
        image = _decode_png(layer.png)
        # viridis middle stop
        assert (image == (33, 145, 140, 255)).all(axis=-1).all()
