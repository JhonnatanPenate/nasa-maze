from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_SERVICE_ROOT = Path(__file__).resolve().parents[3]
_REPO_ROOT = _SERVICE_ROOT.parent


class Settings(BaseSettings):
    """MS5 runtime settings (env prefix ``RISK_``; plan §9.1)."""

    model_config = SettingsConfigDict(env_prefix="RISK_")

    body: str = "mars"
    planet_radius_m: float = 3_396_190.0

    # Upstream datasource mode shared by the MS4 terrain and MS3 raster
    # adapters. `unavailable` builds adapters that always fail upstream.
    datasource_mode: Literal["synthetic", "http", "unavailable"] = "synthetic"
    raster_base_url: str = "http://localhost:8003"
    terrain_base_url: str = "http://localhost:8004"
    upstream_timeout_s: float = 5.0
    upstream_retries: int = 2

    # Environmental climatology catalog (SQLite, read-only at runtime).
    catalog_path: str = str(
        _REPO_ROOT / "data" / "processed" / "mars" / "risk" / "risk_catalog.sqlite"
    )
    seed_catalog_path: str = str(_SERVICE_ROOT / "data" / "seed" / "risk_catalog_seed.sqlite")
    catalog_required: bool = False

    config_dir: str = str(_SERVICE_ROOT / "config")

    default_sol: int = 1360
    default_vehicle_profile: str = "baseline_mars_rover"

    # Request protection caps (plan §9.1).
    max_path_points: int = 1000
    max_samples: int = 1000
    max_area_cells: int = 250_000
    sampling_step_m: float = 90.0

    log_level: str = "INFO"

    @property
    def effective_catalog_path(self) -> str | None:
        """First existing catalog path, or None when neither file exists."""
        for candidate in (self.catalog_path, self.seed_catalog_path):
            if candidate and Path(candidate).is_file():
                return candidate
        return None
