class RasterServiceError(Exception):
    """Base class for every error raised by the Raster Service."""


class RasterValidationError(RasterServiceError):
    """Invalid input: out-of-range coordinates, inverted bbox, bad limits."""


class NotFoundError(RasterServiceError):
    """A requested resource does not exist or has no coverage."""


class UnknownDatasetError(NotFoundError):
    """Dataset name is not registered in the service registry."""


class UnknownBandError(NotFoundError):
    """Band name does not exist in the dataset; message lists valid names."""


class NoCoverageError(NotFoundError):
    """The request area or point does not intersect the dataset extent."""


class DatasetUnavailableError(RasterServiceError):
    """Dataset file is missing, corrupt or fails structural checks."""
