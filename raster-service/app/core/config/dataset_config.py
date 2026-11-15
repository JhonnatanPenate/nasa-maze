from typing import Literal

from pydantic import BaseModel


class DatasetConfig(BaseModel):
    path: str
    kind: Literal["geotiff", "memory"] = "geotiff"
    band_names: list[str] = []
    band_units: dict[str, str] = {
        "pendiente_grados": "deg",
        "rugosidad_m": "m",
        "fraccion_oscura": "fraction",
        "inercia_termica_tiu": "tiu",
        "albedo": "fraction",
        "distancia_duna_m": "m",
    }
    colormaps: dict[str, str] = {
        "pendiente_grados": "slope",
        "albedo": "grayscale",
    }
    default_colormap: str = "viridis"
    value_ranges: dict[str, tuple[float, float]] = {"pendiente_grados": (0.0, 35.0)}
