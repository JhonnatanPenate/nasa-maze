"""Per-soil rover-tilt prediction (plan §4.2, Javi ``_predecir_inclinacion_por_suelo``).

Each soil regime has a linear model ``tilt = intercept + sum(coef * clip(x))``
from the delivered ``modelos_por_suelo.json``; predictors are clipped to the
calibration ``rango_predictores`` and the prediction floored at 0 deg.
Models whose ``estado`` is not ``ajustado`` — and unclassifiable soil — fall
back to ``modelo_global`` (same Javi rule).

Raster predictors (``pendiente_grados``, ``rugosidad``,
``inercia_termica_tiu``, ``albedo``) come from MS4/MS3 samples; daily
predictors (``dosis_rad_uGy_h``, ``temp_suelo_K_media``) come from the
selected sol's hourly profiles, defaulting to 0.0 exactly like Javi's
``predictores_diarios.get(predictor, 0.0)`` before clipping.

Predicted tilt feeds vehicle restrictions and effective speed only — it is
NOT a SPEC factor and never substitutes for MS4 ``slope_deg``.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.domain.soil_type import SoilType

# Raster-layer predictors (MS4 slope reused as pendiente_grados).
RASTER_PREDICTORS = frozenset({"pendiente_grados", "rugosidad", "inercia_termica_tiu", "albedo"})


@dataclass(frozen=True)
class TiltModel:
    """One linear tilt model (per-soil or global fallback)."""

    label: str  # e.g. "arena_dunas" or "global"
    estado: str  # "ajustado" when fitted; anything else -> global fallback
    metodo: str
    predictors: tuple[str, ...]
    coefficients: dict[str, float]
    predictor_ranges: dict[str, tuple[float, float]]
    sigma_residual: float
    r2_ajustado: float


@dataclass(frozen=True)
class TiltModelSet:
    """Parsed ``modelos_por_suelo.json``: 4 soil models + global."""

    global_model: TiltModel
    soil_models: dict[str, TiltModel] = field(default_factory=dict)


@dataclass(frozen=True)
class TiltPrediction:
    """Result of one tilt prediction (clipped, >= 0 deg)."""

    soil: SoilType | None
    model_label: str
    tilt_deg: float
    sigma: float
    r2: float


def predict_tilt(
    models: TiltModelSet,
    *,
    soil: SoilType | None,
    raster_predictors: Mapping[str, float | None],
    daily_predictors: Mapping[str, float] | None = None,
) -> TiltPrediction | None:
    """Predict tilt in degrees; ``None`` when a required raster predictor
    is nodata (missing data is never fabricated)."""
    daily = daily_predictors or {}

    model = models.global_model
    label = "global"
    if soil is not None:
        candidate = models.soil_models.get(soil.value)
        if candidate is not None and candidate.estado == "ajustado":
            model = candidate
            label = soil.value

    tilt = float(model.coefficients.get("(Intercept)", 0.0))
    for predictor in model.predictors:
        if predictor in RASTER_PREDICTORS:
            raw = raster_predictors.get(predictor)
            if raw is None:
                return None
            value = float(raw)
        else:
            value = float(daily.get(predictor, 0.0))
        lo, hi = model.predictor_ranges[predictor]
        tilt += model.coefficients[predictor] * min(max(value, lo), hi)

    return TiltPrediction(
        soil=soil,
        model_label=f"{label}:{model.metodo}",
        tilt_deg=max(0.0, tilt),
        sigma=model.sigma_residual,
        r2=max(model.r2_ajustado, 0.0),
    )
