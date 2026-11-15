"""Runtime configuration via environment variables (section 8)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOCATION_", extra="ignore")

    catalog_path: Path = Path(
        "/app/data/processed/mars/location/location_catalog.sqlite"
    )
    seed_catalog_path: Path = Path("/app/data/seed/location_catalog_seed.sqlite")
    config_dir: Path = Path("/app/config")
    default_body: str = "mars"
    fuzzy_min_score: float = 0.60
    ambiguity_gap: float = 0.05
    max_limit: int = 50
    admin_enabled: bool = False
    # implementation detail: when false the app starts without a catalog and
    # endpoints answer 503 CATALOG_UNAVAILABLE (used by tests / local dev)
    catalog_required: bool = True
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    port: int = Field(default=8001, validation_alias="PORT")
