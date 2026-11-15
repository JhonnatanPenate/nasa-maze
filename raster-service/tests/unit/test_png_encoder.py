import struct
import zlib

import numpy as np
import pytest

from app.infrastructure.rendering.png_encoder import PngEncoder

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunks(data: bytes):
    pos = len(_PNG_SIGNATURE)
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        yield kind, data[pos + 8 : pos + 8 + length]
        pos += 12 + length


def _chunk_map(data: bytes) -> dict[bytes, bytes]:
    return {kind: payload for kind, payload in _chunks(data)}


@pytest.fixture
def encoder() -> PngEncoder:
    return PngEncoder()


class TestEncode:
    def test_produces_png_signature_and_ihdr(self, encoder):
        data = encoder.encode(np.zeros((4, 3, 4), dtype=np.uint8))

        assert data.startswith(_PNG_SIGNATURE)
        ihdr = _chunk_map(data)[b"IHDR"]
        width, height, depth, colour = struct.unpack(">IIBB", ihdr[:10])
        assert (width, height) == (3, 4)
        assert depth == 8
        assert colour == 6  # truecolour RGBA

    def test_idat_inflates_to_filter0_rows_plus_pixels(self, encoder):
        image = np.zeros((2, 3, 4), dtype=np.uint8)
        image[0, 0] = [10, 20, 30, 255]
        image[0, 1] = [40, 50, 60, 200]
        image[1, 2] = [70, 80, 90, 100]

        data = encoder.encode(image)
        raw = zlib.decompress(_chunk_map(data)[b"IDAT"])
        expected = b"".join(b"\x00" + image[i].tobytes() for i in range(2))

        assert raw == expected

    def test_all_transparent_image_is_valid_png(self, encoder):
        image = np.zeros((2, 2, 4), dtype=np.uint8)

        data = encoder.encode(image)

        assert data.startswith(_PNG_SIGNATURE)
        assert _chunk_map(data)[b"IEND"] == b""

    def test_single_pixel_image(self, encoder):
        image = np.array([[[1, 2, 3, 4]]], dtype=np.uint8)

        data = encoder.encode(image)

        ihdr = _chunk_map(data)[b"IHDR"]
        assert struct.unpack(">II", ihdr[:8]) == (1, 1)
        assert zlib.decompress(_chunk_map(data)[b"IDAT"]) == (
            b"\x00\x01\x02\x03\x04"
        )


class TestValidation:
    def test_rejects_2d_array(self, encoder):
        with pytest.raises(ValueError):
            encoder.encode(np.zeros((4, 3), dtype=np.uint8))

    def test_rejects_non_rgba_last_axis(self, encoder):
        with pytest.raises(ValueError):
            encoder.encode(np.zeros((4, 3, 3), dtype=np.uint8))

    def test_rejects_non_uint8_dtype(self, encoder):
        with pytest.raises(ValueError):
            encoder.encode(np.zeros((4, 3, 4), dtype=np.float32))

    @pytest.mark.parametrize("shape", [(0, 3, 4), (3, 0, 4)])
    def test_rejects_zero_width_or_height(self, encoder, shape):
        with pytest.raises(ValueError):
            encoder.encode(np.zeros(shape, dtype=np.uint8))
