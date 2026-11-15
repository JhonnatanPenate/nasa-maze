from fastapi import FastAPI

from app.core.errors.error_handlers import register_exception_handlers
from app.features.datasets.presentation.datasets_router import (
    router as datasets_router,
)
from app.features.health.presentation.health_router import (
    router as health_router,
)
from app.features.point_query.presentation.point_router import (
    router as point_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MS3 Raster Service",
        version="0.1.0",
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(datasets_router)
    app.include_router(point_router)
    return app


app = create_app()
