"""Tilt-model JSON loader: shipped file parses; bad files fail fast."""

import json
from pathlib import Path

import pytest
from app.core.config.tilt_models import load_tilt_models
from app.core.domain.soil_type import SoilType
from app.core.domain.tilt_model import predict_tilt

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_shipped_tilt_models_load() -> None:
    models = load_tilt_models(CONFIG_DIR / "modelos_por_suelo.json")
    assert set(models.soil_models) == {
        "arena_dunas",
        "lecho_rocoso_firme",
        "rocoso_fracturado",
        "regolito_compacto",
    }
    assert models.global_model.label == "global"
    # All delivered soil models are fitted (Javi estado="ajustado").
    assert all(m.estado == "ajustado" for m in models.soil_models.values())


def test_shipped_models_predict_sane_tilt() -> None:
    """Hand-check one prediction against the delivered coefficients:
    regolito_compacto, pendiente=5 (in range 0.25-7.75), rugosidad=0.5
    (in range 0.3-1.08 clipped? no: 0.5 inside), albedo=0.23 (inside
    0.2291-0.2305), dosis missing -> 0.0 -> clipped to lo=10.66."""
    models = load_tilt_models(CONFIG_DIR / "modelos_por_suelo.json")
    result = predict_tilt(
        models,
        soil=SoilType.REGOLITO_COMPACTO,
        raster_predictors={
            "pendiente_grados": 5.0,
            "rugosidad": 0.5,
            "albedo": 0.2300,
        },
        daily_predictors={"dosis_rad_uGy_h": 11.0},
    )
    assert result is not None
    model = models.soil_models["regolito_compacto"]
    expected = model.coefficients["(Intercept)"]
    for predictor, coef in model.coefficients.items():
        if predictor == "(Intercept)":
            continue
        if predictor == "pendiente_grados":
            x = 5.0
        elif predictor == "rugosidad":
            x = 0.5
        elif predictor == "albedo":
            x = 0.2300
        else:  # dosis_rad_uGy_h
            x = 11.0
        lo, hi = model.predictor_ranges[predictor]
        expected += coef * min(max(x, lo), hi)
    assert result.tilt_deg == pytest.approx(max(0.0, expected))
    assert result.sigma == pytest.approx(model.sigma_residual)


def test_missing_file_fails_fast(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot read"):
        load_tilt_models(tmp_path / "nope.json")


def test_invalid_json_fails_fast(tmp_path: Path) -> None:
    bad = tmp_path / "modelos.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_tilt_models(bad)


def test_missing_global_model_fails(tmp_path: Path) -> None:
    bad = tmp_path / "modelos.json"
    bad.write_text(json.dumps({"modelos": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid tilt models"):
        load_tilt_models(bad)


def test_model_without_intercept_fails(tmp_path: Path) -> None:
    bad = tmp_path / "modelos.json"
    bad.write_text(
        json.dumps(
            {
                "modelo_global": {
                    "predictores": ["pendiente_grados"],
                    "coeficientes": {"pendiente_grados": 1.0},
                    "rango_predictores": {"pendiente_grados": [0.0, 10.0]},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Intercept"):
        load_tilt_models(bad)


def test_model_predictor_without_range_fails(tmp_path: Path) -> None:
    bad = tmp_path / "modelos.json"
    bad.write_text(
        json.dumps(
            {
                "modelo_global": {
                    "predictores": ["pendiente_grados"],
                    "coeficientes": {"(Intercept)": 0.0, "pendiente_grados": 1.0},
                    "rango_predictores": {},
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="clipping range"):
        load_tilt_models(bad)
