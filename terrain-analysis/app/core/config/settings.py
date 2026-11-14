from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MS4_")

    body: str = "mars"
    planet_radius_km: float = 3389.5
    datasource_kind: Literal["synthetic", "geotiff", "http"] = "synthetic"
    dem_path: str = ""
    slope_flat_max_deg: float = 5.0
    slope_moderate_max_deg: float = 15.0
    slope_steep_max_deg: float = 30.0
    sample_distance_m: float = 100.0
    max_samples: int = 1000
    max_path_points: int = 100
    max_window_cells: int = 4_000_000
