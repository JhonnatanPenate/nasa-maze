from abc import ABC, abstractmethod

import numpy as np


class ImageEncoder(ABC):
    """Encodes an RGBA image into bytes for a wire format (PNG)."""

    @abstractmethod
    def encode(self, rgba: np.ndarray) -> bytes:
        """rgba: uint8 array of shape (height, width, 4)."""
