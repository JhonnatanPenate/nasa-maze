"""Shared upstream-call guard: bounded retries + error translation.

Read-only upstream calls (MS3/MS4) are idempotent, so retrying transport
failures is safe. Domain errors raised by the wrapped callable
(DomainValidationError/NoCoverageError) are never retried.
"""

from collections.abc import Callable

import httpx

from app.core.errors.exceptions import (
    DomainError,
    UpstreamUnavailableError,
)


def call_with_retries[T](
    fn: Callable[[], T],
    *,
    retries: int,
    what: str,
) -> T:
    """Run ``fn`` retrying transport-level failures up to ``retries``.

    ``httpx.TimeoutException``/``httpx.TransportError`` are retried;
    ``DomainError`` propagates untouched; after the last attempt a
    transport failure becomes ``UpstreamUnavailableError`` (-> HTTP 502).
    """
    attempt = 0
    while True:
        try:
            return fn()
        except DomainError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            attempt += 1
            if attempt > retries:
                raise UpstreamUnavailableError(
                    f"{what} failed after {attempt} attempt(s): {exc}"
                ) from exc
