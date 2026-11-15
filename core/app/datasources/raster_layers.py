import io
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from app.settings import DataUnavailableError

BANDAS = ("pendiente_grados", "rugosidad_m", "fraccion_oscura", "inercia_termica_tiu", "albedo", "distancia_duna_m")
_VIRIDIS = np.array([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]], dtype=float)


def _colorear(norm: np.ndarray, cmap: str) -> np.ndarray:
    if cmap == "gray":
        g = (norm * 255).astype(np.uint8)
        return np.stack([g, g, g], axis=-1)
    pos = norm * (len(_VIRIDIS) - 1)
    lo = np.clip(pos.astype(int), 0, len(_VIRIDIS) - 2)
    t = (pos - lo)[..., None]
    return (_VIRIDIS[lo] * (1 - t) + _VIRIDIS[lo + 1] * t).astype(np.uint8)


def rejilla_bounds(processed: Path) -> tuple[float, float, float, float]:
    try:
        with rasterio.open(processed / "rejilla_ruta_90m.tif") as ds:
            b = ds.bounds
    except rasterio.errors.RasterioIOError as e:
        raise DataUnavailableError(f"rejilla ilegible: {e}") from e
    return (b.left, b.bottom, b.right, b.top)


def render_band(processed: Path, banda: str, cmap: str = "viridis") -> tuple[bytes, tuple[float, float, float, float]]:
    try:
        with rasterio.open(processed / "rejilla_ruta_90m.tif") as ds:
            data = ds.read(BANDAS.index(banda) + 1).astype(float)
            b = ds.bounds
    except rasterio.errors.RasterioIOError as e:
        raise DataUnavailableError(f"rejilla ilegible: {e}") from e
    valid = np.isfinite(data)
    if not valid.any():
        raise DataUnavailableError(f"banda {banda} sin datos válidos")
    lo, hi = data[valid].min(), data[valid].max()
    norm = np.zeros_like(data) if hi == lo else np.where(valid, (data - lo) / (hi - lo), 0.0)
    rgba = np.dstack([_colorear(norm, cmap), np.where(valid, 255, 0).astype(np.uint8)])
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG")
    return buf.getvalue(), (b.left, b.bottom, b.right, b.top)
