"""Loader for ``config/modelos_por_suelo.json`` (Javi tilt models).

The file is a copy of the delivered ``data/gale/processed/
modelos_por_suelo.json`` (see DECISIONS MS5-D19). Parsing is strict enough
to fail fast on a malformed model: every declared predictor needs a
coefficient and a clipping range, and ``(Intercept)`` must exist.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.core.domain.tilt_model import TiltModel, TiltModelSet


class _TiltModelSchema(BaseModel):
    estado: str = ""
    metodo: str = ""
    predictores: list[str] = Field(default_factory=list)
    coeficientes: dict[str, float] = Field(default_factory=dict)
    rango_predictores: dict[str, list[float]] = Field(default_factory=dict)
    sigma_residual: float = 0.0
    r2_ajustado: float = 0.0

    @model_validator(mode="after")
    def _consistent(self) -> "_TiltModelSchema":
        if "(Intercept)" not in self.coeficientes:
            raise ValueError("tilt model lacks '(Intercept)' coefficient")
        for predictor in self.predictores:
            if predictor not in self.coeficientes:
                raise ValueError(f"tilt model predictor '{predictor}' has no coefficient")
            if predictor not in self.rango_predictores:
                raise ValueError(f"tilt model predictor '{predictor}' has no clipping range")
            lo, hi = self.rango_predictores[predictor]
            if not lo < hi:
                raise ValueError(f"tilt model predictor '{predictor}' range must satisfy lo < hi")
        return self


class _TiltFileSchema(BaseModel):
    modelos: dict[str, _TiltModelSchema] = Field(default_factory=dict)
    modelo_global: _TiltModelSchema


def _to_domain(label: str, raw: _TiltModelSchema) -> TiltModel:
    return TiltModel(
        label=label,
        estado=raw.estado,
        metodo=raw.metodo,
        predictors=tuple(raw.predictores),
        coefficients=dict(raw.coeficientes),
        predictor_ranges={
            name: (float(bounds[0]), float(bounds[1]))
            for name, bounds in raw.rango_predictores.items()
        },
        sigma_residual=raw.sigma_residual,
        r2_ajustado=raw.r2_ajustado,
    )


def load_tilt_models(path: str | Path) -> TiltModelSet:
    """Parse ``modelos_por_suelo.json`` into a ``TiltModelSet``.

    Fails fast (``ValueError``) on unreadable/invalid JSON or an
    inconsistent model table.
    """
    file_path = Path(path)
    try:
        raw: Any = json.loads(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read tilt models {file_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {file_path}: {exc}") from exc
    try:
        parsed = _TiltFileSchema.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Invalid tilt models in {file_path}: {exc}") from exc
    return TiltModelSet(
        global_model=_to_domain("global", parsed.modelo_global),
        soil_models={soil: _to_domain(soil, model) for soil, model in parsed.modelos.items()},
    )
