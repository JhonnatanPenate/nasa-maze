"""Exception -> application/problem+json handlers (section 6.6)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from location_service.errors import AppError, InvalidParameterError

logger = logging.getLogger("location_service.errors")

_PROBLEM_BASE = "https://planetary-explorer.local/errors"


def _problem(
    request: Request,
    *,
    code: str,
    status: int,
    title: str,
    detail: str,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"{_PROBLEM_BASE}/{code.lower().replace('_', '-')}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
            "request_id": request_id,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _problem(
            request,
            code=exc.code,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        parts = []
        for err in exc.errors()[:5]:
            loc = ".".join(str(p) for p in err.get("loc", ()))
            parts.append(f"{loc}: {err.get('msg', 'invalid')}" if loc else str(err.get("msg")))
        err = InvalidParameterError("; ".join(parts) or "invalid request")
        return _problem(
            request, code=err.code, status=err.status, title=err.title, detail=err.detail
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # e.g. 404 for unknown routes -> keep problem+json shape
        return _problem(
            request,
            code="INVALID_PARAMETER" if exc.status_code < 500 else "INTERNAL_ERROR",
            status=exc.status_code,
            title="Request error",
            detail=str(exc.detail),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error request_id=%s", getattr(request.state, "request_id", "?"))
        return _problem(
            request,
            code="INTERNAL_ERROR",
            status=500,
            title="Internal error",
            detail="internal server error",
        )
