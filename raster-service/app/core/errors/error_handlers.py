from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors.exceptions import (
    DatasetUnavailableError,
    NotFoundError,
    RasterServiceError,
    RasterValidationError,
)

_STATUS_BY_ERROR: dict[type[RasterServiceError], int] = {
    RasterValidationError: 400,
    NotFoundError: 404,
    DatasetUnavailableError: 503,
}


def _status_for(error: RasterServiceError) -> int:
    for error_type in type(error).__mro__:
        status = _STATUS_BY_ERROR.get(error_type)
        if status is not None:
            return status
    return 500


async def _handle_raster_error(
    request: Request, error: RasterServiceError
) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for(error), content={"detail": str(error)}
    )


async def _handle_unexpected_error(
    request: Request, error: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=500, content={"detail": "internal error"}
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RasterServiceError, _handle_raster_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
