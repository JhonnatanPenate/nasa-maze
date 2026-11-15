"""FastAPI application factory (create_app + lifespan catalog load)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request, Response

from location_service.adapters.memory_index import MemoryIndex
from location_service.adapters.sqlite_catalog import load_catalog
from location_service.api.errors import register_error_handlers
from location_service.api.routers import health, meta, places, regions, resolve
from location_service.settings import Settings

logger = logging.getLogger("location_service")

_INGEST_COMMAND = (
    "python -m location_service.ingest build "
    "--mission data/gale/processed/gale_puntos_quimica.xlsx "
    "--config location-service/config "
    "--out data/processed/mars/location/location_catalog.sqlite"
)


def _type_translations(config_dir: Path) -> dict[str, str]:
    path = Path(config_dir) / "gazetteer_columns.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {
            str(k): str(v)
            for k, v in (data.get("type_word_translations") or {}).items()
        }
    except Exception:
        return {}


def _load_index(settings: Settings) -> MemoryIndex | None:
    path = Path(settings.catalog_path)
    if not path.exists():
        seed = Path(settings.seed_catalog_path)
        if seed.exists():
            logger.warning(
                "catalog %s not found; falling back to seed catalog %s", path, seed
            )
            path = seed
        elif settings.catalog_required:
            raise SystemExit(
                f"location catalog not found: {settings.catalog_path} "
                f"(seed fallback {settings.seed_catalog_path} also missing).\n"
                f"Build it with:\n  {_INGEST_COMMAND}"
            )
        else:
            logger.error("no catalog available; endpoints will return 503")
            return None
    data = load_catalog(path)
    index = MemoryIndex.from_data(
        data,
        fuzzy_min_ratio=settings.fuzzy_min_score * 100.0,
        type_word_translations=_type_translations(settings.config_dir),
    )
    logger.info(
        "catalog loaded: %s (%d places, version %s)",
        path,
        len(data.places),
        data.meta.get("catalog_version", "unknown"),
    )
    return index


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(level=settings.log_level)
        app.state.index = _load_index(settings)
        yield
        app.state.index = None

    app = FastAPI(
        title="Planetary Explorer - Location Service",
        version="0.1.0",
        description=(
            "Mars location resolution: names, ids and coordinates "
            "-> validated planetary coordinates."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.index = None

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        import uuid

        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(places.router)
    app.include_router(resolve.router)
    app.include_router(regions.router)
    app.include_router(meta.router)
    return app


app = create_app()
