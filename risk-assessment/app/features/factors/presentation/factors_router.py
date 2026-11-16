from fastapi import APIRouter, Depends

from app.composition.dependencies import (
    get_environment_repository,
    get_raster_source,
    get_risk_weights,
    get_settings,
    get_terrain_source,
)
from app.core.config.risk_config import RiskWeightsConfig
from app.core.config.settings import Settings
from app.core.domain.factor_assessment import FactorAssessment
from app.core.domain.factor_catalog import (
    DEFAULT_WEIGHTS,
    FACTOR_DUNES,
    FACTOR_RADIATION,
    FACTOR_ROUGHNESS,
    FACTOR_SLOPE,
    FACTOR_TEMPERATURE,
)
from app.core.ports.environment_repository import EnvironmentRepository
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.features.factors.presentation.factors_mapper import FactorsMapper
from app.features.factors.presentation.factors_schemas import FactorsResponse

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/factors", response_model=FactorsResponse)
def list_factors(
    terrain: TerrainSource = Depends(get_terrain_source),
    raster: RasterSource = Depends(get_raster_source),
    environment: EnvironmentRepository = Depends(get_environment_repository),
    weights_config: RiskWeightsConfig = Depends(get_risk_weights),
    settings: Settings = Depends(get_settings),
) -> FactorsResponse:
    """SPEC factor catalog + current data coverage (SPEC §3.3).

    `available` reflects whether each factor's datasource currently has
    coverage (upstream ping + environmental sols present)."""
    terrain_ok = terrain.ping()
    raster_ok = raster.ping()
    env_ok = environment.ping()
    bands = set(raster.dataset_bands()) if raster_ok else set()
    rems_sols = environment.available_sols("rems") if env_ok else ()
    rad_sols = environment.available_sols("rad") if env_ok else ()

    assessments = {
        FACTOR_SLOPE: FactorAssessment(factor_id=FACTOR_SLOPE, available=terrain_ok),
        FACTOR_ROUGHNESS: FactorAssessment(
            factor_id=FACTOR_ROUGHNESS,
            available=raster_ok and "rugosidad_m" in bands,
        ),
        FACTOR_DUNES: FactorAssessment(
            factor_id=FACTOR_DUNES,
            available=raster_ok and {"distancia_duna_m", "fraccion_oscura"} <= bands,
        ),
        FACTOR_TEMPERATURE: FactorAssessment(
            factor_id=FACTOR_TEMPERATURE, available=bool(rems_sols)
        ),
        FACTOR_RADIATION: FactorAssessment(factor_id=FACTOR_RADIATION, available=bool(rad_sols)),
    }
    return FactorsMapper.to_response(
        assessments=assessments,
        weights=weights_config.weights or dict(DEFAULT_WEIGHTS),
        model_version=weights_config.model_version,
        default_sol=settings.default_sol,
        rems_sols=rems_sols,
        rad_sols=rad_sols,
    )
