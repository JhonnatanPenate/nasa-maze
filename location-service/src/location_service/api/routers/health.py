"""Liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from location_service.api.schemas import HealthStatus
from location_service.errors import CatalogUnavailableError

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/ready")
def ready(request: Request) -> HealthStatus:
    if getattr(request.app.state, "index", None) is None:
        raise CatalogUnavailableError("catalog is not loaded")
    return HealthStatus(status="ready")
