from fastapi import APIRouter, Depends

from app.composition.dependencies import (
    get_environment_repository,
    get_raster_source,
    get_risk_thresholds,
    get_risk_weights,
    get_settings,
    get_terrain_source,
)
from app.core.config.risk_config import (
    RiskThresholdsConfig,
    RiskWeightsConfig,
)
from app.core.config.settings import Settings
from app.core.ports.environment_repository import EnvironmentRepository
from app.core.ports.raster_source import RasterSource
from app.core.ports.terrain_source import TerrainSource
from app.features.meta.presentation.meta_schemas import MetaResponse

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/meta", response_model=MetaResponse)
def get_meta(
    terrain: TerrainSource = Depends(get_terrain_source),
    raster: RasterSource = Depends(get_raster_source),
    environment: EnvironmentRepository = Depends(get_environment_repository),
    weights_config: RiskWeightsConfig = Depends(get_risk_weights),
    thresholds_config: RiskThresholdsConfig = Depends(get_risk_thresholds),
    settings: Settings = Depends(get_settings),
) -> MetaResponse:
    """Plan extension: configuration, provenance and coverage snapshot."""
    catalog_path = settings.effective_catalog_path
    return MetaResponse(
        service="risk-assessment",
        model_version=weights_config.model_version,
        weights=(
            weights_config.weights
            if weights_config.weights
            else {
                "slope": 0.4,
                "dunes": 0.2,
                "roughness": 0.15,
                "temperature": 0.15,
                "radiation": 0.1,
            }
        ),
        thresholds=thresholds_config.model_dump(mode="json"),
        default_sol=settings.default_sol,
        default_vehicle_profile=settings.default_vehicle_profile,
        datasource_mode=settings.datasource_mode,
        upstream={
            "terrain": "ok" if terrain.ping() else "unavailable",
            "raster": "ok" if raster.ping() else "unavailable",
            "environment": "ok" if environment.ping() else "unavailable",
        },
        catalog={
            "path": catalog_path,
            "available": catalog_path is not None,
            "rems_sols": list(environment.available_sols("rems")),
            "rad_sols": list(environment.available_sols("rad")),
        },
        coordinate_system={
            "crs": "IAU_2015:49900",
            "lat_type": "planetocentric",
            "lon_convention": "east_positive",
            "lon_range": [-180.0, 180.0],
            "radius_m": settings.planet_radius_m,
        },
    )
