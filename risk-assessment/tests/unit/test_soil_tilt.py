"""Soil classification precedence + tilt prediction (Javi optimizer rules)."""

import pytest
from app.core.domain.soil_type import SoilType, classify_soil
from app.core.domain.tilt_model import (
    TiltModel,
    TiltModelSet,
    predict_tilt,
)


def _soil_kwargs(**overrides: float) -> dict:
    base = {
        "rugosidad_m": 0.8,
        "pendiente_grados": 5.0,
        "albedo": 0.2300,
        "distancia_duna_m": 100.0,
        "fraccion_oscura": 0.2,
    }
    base.update(overrides)
    return base


# --- classify_soil ---------------------------------------------------------


def test_default_regolito_compacto() -> None:
    assert classify_soil(**_soil_kwargs()) is SoilType.REGOLITO_COMPACTO


def test_rocoso_fracturado_rules() -> None:
    assert classify_soil(**_soil_kwargs(rugosidad_m=1.10)) is SoilType.ROCOSO_FRACTURADO
    assert classify_soil(**_soil_kwargs(pendiente_grados=8.0)) is SoilType.ROCOSO_FRACTURADO
    assert classify_soil(**_soil_kwargs(albedo=0.2290)) is SoilType.ROCOSO_FRACTURADO


def test_lecho_rocoso_firme_rules() -> None:
    assert (
        classify_soil(**_soil_kwargs(rugosidad_m=0.60, pendiente_grados=7.0, albedo=0.2294))
        is SoilType.LECHO_ROCOSO_FIRME
    )


def test_arena_dunas_overrides_everything() -> None:
    # Even a rocky steep cell becomes arena_dunas (Javi overwrite order).
    assert (
        classify_soil(
            **_soil_kwargs(
                rugosidad_m=2.0,
                pendiente_grados=20.0,
                albedo=0.2000,
                distancia_duna_m=0.0,
                fraccion_oscura=0.9,
            )
        )
        is SoilType.ARENA_DUNAS
    )
    assert classify_soil(**_soil_kwargs(fraccion_oscura=0.5)) is SoilType.ARENA_DUNAS


def test_albedo_gap_is_regolito() -> None:
    # albedo 0.2292 sits between rocoso (<0.2291) and firme (>=0.2294).
    assert classify_soil(**_soil_kwargs(albedo=0.2292)) is SoilType.REGOLITO_COMPACTO


def test_any_nodata_input_returns_none() -> None:
    for key in (
        "rugosidad_m",
        "pendiente_grados",
        "albedo",
        "distancia_duna_m",
        "fraccion_oscura",
    ):
        kwargs = _soil_kwargs()
        kwargs[key] = None  # type: ignore[dict-item]
        assert classify_soil(**kwargs) is None, key


# --- predict_tilt ----------------------------------------------------------


def _model_set() -> TiltModelSet:
    global_model = TiltModel(
        label="global",
        estado="ajustado",
        metodo="test_global",
        predictors=("pendiente_grados", "rugosidad"),
        coefficients={
            "(Intercept)": 1.0,
            "pendiente_grados": 2.0,
            "rugosidad": 10.0,
        },
        predictor_ranges={
            "pendiente_grados": (0.0, 20.0),
            "rugosidad": (0.0, 5.0),
        },
        sigma_residual=2.0,
        r2_ajustado=0.5,
    )
    arena = TiltModel(
        label="arena_dunas",
        estado="ajustado",
        metodo="test_arena",
        predictors=("pendiente_grados",),
        coefficients={"(Intercept)": 0.5, "pendiente_grados": 1.0},
        predictor_ranges={"pendiente_grados": (0.0, 10.0)},
        sigma_residual=1.0,
        r2_ajustado=0.4,
    )
    rocoso = TiltModel(
        label="rocoso_fracturado",
        estado="no_ajustado",  # forces global fallback like Javi
        metodo="test_rocoso",
        predictors=("pendiente_grados",),
        coefficients={"(Intercept)": 99.0, "pendiente_grados": 99.0},
        predictor_ranges={"pendiente_grados": (0.0, 10.0)},
        sigma_residual=9.0,
        r2_ajustado=0.1,
    )
    return TiltModelSet(
        global_model=global_model,
        soil_models={"arena_dunas": arena, "rocoso_fracturado": rocoso},
    )


def test_predict_tilt_per_soil_model() -> None:
    models = _model_set()
    result = predict_tilt(
        models,
        soil=SoilType.ARENA_DUNAS,
        raster_predictors={"pendiente_grados": 3.0, "rugosidad": 1.0},
    )
    assert result is not None
    # arena model: 0.5 + 1.0 * clip(3.0, 0, 10) = 3.5
    assert result.tilt_deg == pytest.approx(3.5)
    assert result.sigma == 1.0
    assert result.model_label == "arena_dunas:test_arena"
    assert result.soil is SoilType.ARENA_DUNAS


def test_predict_tilt_global_fallback_for_unadjusted_model() -> None:
    models = _model_set()
    result = predict_tilt(
        models,
        soil=SoilType.ROCOSO_FRACTURADO,
        raster_predictors={"pendiente_grados": 4.0, "rugosidad": 2.0},
    )
    assert result is not None
    # global: 1.0 + 2.0*4 + 10.0*2 = 29.0; label marks the fallback.
    assert result.tilt_deg == pytest.approx(29.0)
    assert result.model_label == "global:test_global"


def test_predict_tilt_unclassifiable_soil_uses_global() -> None:
    models = _model_set()
    result = predict_tilt(
        models,
        soil=None,
        raster_predictors={"pendiente_grados": 4.0, "rugosidad": 2.0},
    )
    assert result is not None
    assert result.tilt_deg == pytest.approx(29.0)
    assert result.model_label == "global:test_global"
    assert result.soil is None


def test_predict_tilt_clips_predictors() -> None:
    models = _model_set()
    result = predict_tilt(
        models,
        soil=SoilType.ARENA_DUNAS,
        raster_predictors={"pendiente_grados": 99.0, "rugosidad": 1.0},
    )
    assert result is not None
    # clip(99, 0, 10) = 10 -> 0.5 + 10 = 10.5
    assert result.tilt_deg == pytest.approx(10.5)


def test_predict_tilt_negative_floored_at_zero() -> None:
    models = TiltModelSet(
        global_model=TiltModel(
            label="global",
            estado="ajustado",
            metodo="m",
            predictors=("pendiente_grados",),
            coefficients={"(Intercept)": -50.0, "pendiente_grados": 1.0},
            predictor_ranges={"pendiente_grados": (0.0, 10.0)},
            sigma_residual=1.0,
            r2_ajustado=0.0,
        )
    )
    result = predict_tilt(models, soil=None, raster_predictors={"pendiente_grados": 1.0})
    assert result is not None
    assert result.tilt_deg == 0.0
    assert result.r2 == 0.0  # max(r2, 0) like Javi


def test_predict_tilt_missing_raster_predictor_returns_none() -> None:
    models = _model_set()
    result = predict_tilt(
        models,
        soil=SoilType.ARENA_DUNAS,
        raster_predictors={"pendiente_grados": 3.0, "rugosidad": None},
    )
    # arena model does not use rugosidad -> still predicts
    assert result is not None and result.tilt_deg == pytest.approx(3.5)
    # global model DOES use rugosidad -> nodata -> None
    result_global = predict_tilt(
        models,
        soil=SoilType.REGOLITO_COMPACTO,  # not in soil_models -> global
        raster_predictors={"pendiente_grados": 3.0, "rugosidad": None},
    )
    assert result_global is None


def test_predict_tilt_daily_predictors_default_and_clip() -> None:
    models = TiltModelSet(
        global_model=TiltModel(
            label="global",
            estado="ajustado",
            metodo="m",
            predictors=("dosis_rad_uGy_h",),
            coefficients={"(Intercept)": 0.0, "dosis_rad_uGy_h": 1.0},
            predictor_ranges={"dosis_rad_uGy_h": (10.0, 12.0)},
            sigma_residual=1.0,
            r2_ajustado=0.3,
        )
    )
    # Missing daily predictor -> 0.0 -> clipped to lo=10 -> tilt 10.
    result = predict_tilt(models, soil=None, raster_predictors={})
    assert result is not None and result.tilt_deg == pytest.approx(10.0)
    # Provided value clipped to hi=12.
    result2 = predict_tilt(
        models,
        soil=None,
        raster_predictors={},
        daily_predictors={"dosis_rad_uGy_h": 50.0},
    )
    assert result2 is not None and result2.tilt_deg == pytest.approx(12.0)
