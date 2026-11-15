"""Application errors mapped to RFC 7807 problem+json (section 6.6)."""

from __future__ import annotations


class AppError(Exception):
    """Base class: carries the problem+json fields."""

    code = "INTERNAL_ERROR"
    status = 500
    title = "Internal error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail or self.title


class InvalidParameterError(AppError):
    code = "INVALID_PARAMETER"
    status = 422
    title = "Invalid parameter"


class OutOfRangeError(AppError):
    code = "OUT_OF_RANGE"
    status = 422
    title = "Coordinate out of range"


class UnsupportedBodyError(AppError):
    code = "UNSUPPORTED_BODY"
    status = 422
    title = "Unsupported body"


class UnsupportedCoordinateSystemError(AppError):
    code = "UNSUPPORTED_COORDINATE_SYSTEM"
    status = 422
    title = "Unsupported coordinate system"


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status = 404
    title = "Not found"


class CatalogUnavailableError(AppError):
    code = "CATALOG_UNAVAILABLE"
    status = 503
    title = "Catalog unavailable"
