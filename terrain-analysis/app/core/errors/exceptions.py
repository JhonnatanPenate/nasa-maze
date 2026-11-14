class DomainError(Exception):
    """Base class for all errors raised by the terrain analysis domain."""


class DomainValidationError(DomainError):
    """Input failed domain validation. Maps to HTTP 400."""


class NoCoverageError(DomainError):
    """Requested location hits nodata or lies outside the DEM extent. Maps to HTTP 404."""


class UpstreamDatasourceError(DomainError):
    """The raster datasource failed. Maps to HTTP 502."""
