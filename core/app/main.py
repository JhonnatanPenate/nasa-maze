from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import health, layers, models, places, routes
from app.settings import DataUnavailableError


def create_app() -> FastAPI:
    app = FastAPI(title="Core — Planetary Explorer", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Bounds"],
    )

    @app.exception_handler(DataUnavailableError)
    def _data_unavailable(_: Request, exc: DataUnavailableError):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    for r in (health, routes, layers, models, places):
        app.include_router(r.router)
    return app


app = create_app()
