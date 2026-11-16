"""SPEC factor catalog ids (SPEC_MS5 §3.1) and default weights (§5).

Weights are the SPEC defaults; the runtime source of truth is
``config/risk_weights.yaml`` loaded via ``core.config.risk_config``.
"""

FACTOR_SLOPE = "slope"
FACTOR_ROUGHNESS = "roughness"
FACTOR_DUNES = "dunes"
FACTOR_TEMPERATURE = "temperature"
FACTOR_RADIATION = "radiation"

SPEC_FACTORS: tuple[str, ...] = (
    FACTOR_SLOPE,
    FACTOR_ROUGHNESS,
    FACTOR_DUNES,
    FACTOR_TEMPERATURE,
    FACTOR_RADIATION,
)

DEFAULT_WEIGHTS: dict[str, float] = {
    FACTOR_SLOPE: 0.4,
    FACTOR_DUNES: 0.2,
    FACTOR_ROUGHNESS: 0.15,
    FACTOR_TEMPERATURE: 0.15,
    FACTOR_RADIATION: 0.1,
}
