from fastapi import FastAPI

from app.core.errors.error_handlers import register_exception_handlers
from app.features.area_assessment.presentation.area_router import (
    router as area_router,
)
from app.features.factors.presentation.factors_router import (
    router as factors_router,
)
from app.features.health.presentation.health_router import (
    router as health_router,
)
from app.features.meta.presentation.meta_router import router as meta_router
from app.features.path_assessment.presentation.path_router import (
    router as path_router,
)
from app.features.point_assessment.presentation.point_router import (
    router as point_router,
)
from app.features.vehicle_profiles.presentation.vehicle_profiles_router import (
    router as vehicle_profiles_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MS5 Risk Assessment Service",
        version="0.1.0",
    )
    register_exception_handlers(app)
    # Fail fast on invalid YAML config at startup (plan §5).
    from app.composition.dependencies import get_settings
    from app.core.config.risk_config import (
        load_thresholds,
        load_vehicle_profiles,
        load_weights,
    )

    _settings = get_settings()
    load_weights(_settings.config_dir)
    load_thresholds(_settings.config_dir)
    load_vehicle_profiles(_settings.config_dir)

    app.include_router(health_router)
    app.include_router(point_router)
    app.include_router(path_router)
    app.include_router(factors_router)
    app.include_router(vehicle_profiles_router)
    app.include_router(meta_router)
    app.include_router(area_router)
    return app


app = create_app()
