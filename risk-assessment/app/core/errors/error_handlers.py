from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors.exceptions import (
    AreaTooLargeError,
    ClimatologyUnavailableError,
    DomainError,
    DomainValidationError,
    NoCoverageError,
    UpstreamUnavailableError,
    VehicleProfileNotFoundError,
)

# Shared MS3/MS4 error-body format: {"detail": "..."}. Plan-named error codes
# are prefixed into the detail string so the body stays a plain string while
# remaining machine-greppable (docs/DECISIONS.md).
_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    DomainValidationError: 400,
    NoCoverageError: 404,
    VehicleProfileNotFoundError: 404,
    AreaTooLargeError: 422,
    UpstreamUnavailableError: 502,
    ClimatologyUnavailableError: 503,
}


def _status_for(error: DomainError) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status
    return 500


async def _handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    message = str(error)
    if error.code:
        message = f"{error.code}: {message}"
    return JSONResponse(status_code=_status_for(error), content={"detail": message})


async def _handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    # Sanitized 500: never leak internals (plan §7.3 INTERNAL_ERROR).
    return JSONResponse(
        status_code=500,
        content={"detail": "INTERNAL_ERROR: unexpected server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected_error)
