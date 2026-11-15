from collections.abc import Callable
from typing import TypeVar

from app.core.errors.exceptions import DomainError, UpstreamDatasourceError

T = TypeVar("T")


def guarded_call(call: Callable[[], T]) -> T:
    """Run a datasource call mapping failures onto the domain taxonomy.

    DomainError subclasses pass through unchanged; every other exception
    is wrapped in UpstreamDatasourceError (chained via `from`).
    """
    try:
        return call()
    except DomainError:
        raise
    except Exception as exc:
        raise UpstreamDatasourceError(
            f"Raster datasource request failed: {exc}"
        ) from exc
