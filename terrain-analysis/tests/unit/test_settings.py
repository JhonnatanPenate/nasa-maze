from app.core.config.settings import Settings


def test_settings_defaults():
    settings = Settings()

    assert settings.body == "mars"
    assert settings.planet_radius_km == 3396.19
    assert settings.datasource_kind == "synthetic"
    assert settings.dem_path == ""
    assert settings.rejilla_path == "data/gale/processed/rejilla_ruta_90m.tif"
    assert settings.rejilla_slope_band == 1
    assert settings.slope_flat_max_deg == 5.0
    assert settings.slope_moderate_max_deg == 15.0
    assert settings.slope_steep_max_deg == 30.0
    assert settings.sample_distance_m == 100.0
    assert settings.max_samples == 1000
    assert settings.max_path_points == 100
    assert settings.max_window_cells == 4_000_000


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("MS4_MAX_SAMPLES", "42")

    assert Settings().max_samples == 42


def test_datasource_kind_accepts_rejilla():
    assert Settings(datasource_kind="rejilla").datasource_kind == "rejilla"
