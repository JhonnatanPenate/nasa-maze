"""Settings defaults and env overrides (RISK_ prefix)."""

from app.core.config.settings import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.datasource_mode == "synthetic"
    assert settings.default_sol == 1360
    assert settings.default_vehicle_profile == "baseline_mars_rover"
    assert settings.raster_base_url == "http://localhost:8003"
    assert settings.terrain_base_url == "http://localhost:8004"


def test_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("RISK_DATASOURCE_MODE", "http")
    monkeypatch.setenv("RISK_DEFAULT_SOL", "2140")
    settings = Settings(_env_file=None)
    assert settings.datasource_mode == "http"
    assert settings.default_sol == 2140


def test_effective_catalog_path_none_when_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(
        _env_file=None,
        catalog_path=str(tmp_path / "nope.sqlite"),
        seed_catalog_path=str(tmp_path / "also-nope.sqlite"),
    )
    assert settings.effective_catalog_path is None
