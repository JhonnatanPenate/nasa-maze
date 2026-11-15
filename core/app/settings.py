from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
AOI = (137.345, -4.740, 137.455, -4.580)  # west, south, east, north (IAU_2015:49900)
SOLS = (1360, 2140, 3290, 4710)


class DataUnavailableError(Exception):
    """Un archivo del paquete data/gale no existe o no se pudo leer."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORE_", env_file=".env", extra="ignore")

    data_dir: str = "data/gale"
    ms6_url: str = ""
    ms4_url: str = ""
    ms1_url: str = ""
    route_timeout_s: float = 120.0
    health_timeout_s: float = 2.0
    search_timeout_s: float = 5.0
    precalc_fallback: bool = True
    bradbury_lon: float = 137.4416
    bradbury_lat: float = -4.5895

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def processed(self) -> Path:
        return self.data_path / "processed"

    @property
    def raw(self) -> Path:
        return self.data_path / "raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()
