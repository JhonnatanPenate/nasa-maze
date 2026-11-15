import logging
from collections.abc import Callable
from typing import TypeVar

from app.core.errors.exceptions import (
    DatasetUnavailableError,
    RasterServiceError,
)

T = TypeVar("T")

_logger = logging.getLogger(__name__)


def guarded_call(dataset: str, call: Callable[[], T]) -> T:
    """Run a datasource call mapping failures onto the service taxonomy.

    RasterServiceError subclasses pass through unchanged; every other
    exception is logged with its original detail and re-raised as a
    generic DatasetUnavailableError (chained via `from`), so internal
    errors and file paths never leak into HTTP responses.
    """
    try:
        return call()
    except RasterServiceError:
        raise
    except Exception as exc:
        _logger.warning("Dataset %r is unavailable: %s", dataset, exc)
        raise DatasetUnavailableError(
            f"Dataset {dataset!r} is unavailable"
        ) from exc
