class DomainError(Exception):
    """Base class for all errors raised by the risk assessment domain."""

    code: str | None = None


class DomainValidationError(DomainError):
    """Input failed domain validation. Maps to HTTP 400."""


class NoCoverageError(DomainError):
    """Requested location has no data coverage. Maps to HTTP 404."""


class UpstreamUnavailableError(DomainError):
    """An upstream service (MS3/MS4) failed or is unreachable. Maps to HTTP 502."""


class ClimatologyUnavailableError(DomainError):
    """The local environmental catalog is missing or unreadable. Maps to HTTP 503."""

    code = "CLIMATOLOGY_UNAVAILABLE"


class VehicleProfileNotFoundError(DomainError):
    """Unknown vehicle profile id. Maps to HTTP 404."""

    code = "VEHICLE_PROFILE_NOT_FOUND"


class AreaTooLargeError(DomainError):
    """Area request exceeds the configured cell cap. Maps to HTTP 422."""

    code = "AREA_TOO_LARGE"
