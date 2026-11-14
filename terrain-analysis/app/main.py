from fastapi import FastAPI

from app.core.errors.error_handlers import register_exception_handlers
from app.features.area_analysis.presentation.area_router import (
    router as area_router,
)
from app.features.health.presentation.health_router import (
    router as health_router,
)
from app.features.point_analysis.presentation.point_router import (
    router as point_router,
)
from app.features.profile_analysis.presentation.profile_router import (
    router as profile_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MS4 Terrain Analysis Service",
        version="0.1.0",
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(point_router)
    app.include_router(profile_router)
    app.include_router(area_router)
    return app


app = create_app()
