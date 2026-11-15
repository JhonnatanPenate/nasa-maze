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
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status
    return 500


async def _handle_raster_error(
    request: Request, error: RasterServiceError
) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for(error), content={"detail": str(error)}
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RasterServiceError, _handle_raster_error)
