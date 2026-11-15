from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MS4_")

    body: str = "mars"
    planet_radius_km: float = 3396.19
    datasource_kind: Literal["synthetic", "geotiff", "rejilla", "http"] = "synthetic"
    dem_path: str = ""
    rejilla_path: str = str(
        _REPO_ROOT / "data" / "gale" / "processed" / "rejilla_ruta_90m.tif"
    )
    rejilla_slope_band: int = 1
    slope_flat_max_deg: float = 5.0
    slope_moderate_max_deg: float = 15.0
    slope_steep_max_deg: float = 30.0
    sample_distance_m: float = 100.0
    max_samples: int = 1000
    max_path_points: int = 100
    max_window_cells: int = 4_000_000
