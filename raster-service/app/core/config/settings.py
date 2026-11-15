from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.dataset_config import DatasetConfig

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MS3_")

    planet_radius_km: float = 3396.19
    crs_label: str = "IAU_2015:49900"
    rejilla_path: str = str(
        _REPO_ROOT / "data" / "gale" / "processed" / "rejilla_ruta_90m.tif"
    )
    datasets: dict[str, DatasetConfig] | None = None
    max_window_cells: int = 1_000_000
    max_path_points: int = 100
    max_samples: int = 1000

    @model_validator(mode="after")
    def _default_registry(self) -> "Settings":
        if self.datasets is None:
            self.datasets = {"rejilla": DatasetConfig(path=self.rejilla_path)}
        return self
