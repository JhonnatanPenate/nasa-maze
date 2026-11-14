from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors.exceptions import (
    DomainError,
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    DomainValidationError: 400,
    NoCoverageError: 404,
    UpstreamDatasourceError: 502,
}


def _status_for(error: DomainError) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status
    return 500


async def _handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    return JSONResponse(status_code=_status_for(error), content={"detail": str(error)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
