import struct
import zlib

import numpy as np

from app.core.ports.image_encoder import ImageEncoder

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_BIT_DEPTH_RGBA8 = 8
_COLOUR_TYPE_RGBA = 6


class PngEncoder(ImageEncoder):
    """Encodes an H x W x 4 uint8 RGBA array as a PNG using only the
    stdlib (zlib + struct). One filter byte 0 per row; no dependencies.
    """

    def encode(self, rgba: np.ndarray) -> bytes:
        image = np.asarray(rgba)
        if image.ndim != 3 or image.shape[2] != 4:
            raise ValueError(
                f"rgba must have shape (height, width, 4), "
                f"got {image.shape}"
            )
        if image.dtype != np.uint8:
            raise ValueError(
                f"rgba must be uint8, got {image.dtype}"
            )
        height, width = image.shape[0], image.shape[1]
        if width < 1 or height < 1:
            raise ValueError(
                f"rgba must be at least 1x1 pixel, got {image.shape}"
            )
        raw = b"".join(
            b"\x00" + image[row].tobytes() for row in range(height)
        )
        ihdr = struct.pack(
            ">IIBBBBB",
            width,
            height,
            _BIT_DEPTH_RGBA8,
            _COLOUR_TYPE_RGBA,
            0,
            0,
            0,
        )
        return (
            _PNG_SIGNATURE
            + self._chunk(b"IHDR", ihdr)
            + self._chunk(b"IDAT", zlib.compress(raw))
            + self._chunk(b"IEND", b"")
        )

    @staticmethod
    def _chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )
