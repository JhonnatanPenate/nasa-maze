import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors.error_handlers import register_exception_handlers
from app.core.errors.exceptions import (
    DomainError,
    DomainValidationError,
    NoCoverageError,
    UpstreamDatasourceError,
)


def _client_raising(error: Exception) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise error

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (DomainValidationError("bad input"), 400),
        (NoCoverageError("nodata"), 404),
        (UpstreamDatasourceError("down"), 502),
        (DomainError("unknown"), 500),
    ],
)
def test_domain_errors_map_to_http_status(error, status):
    response = _client_raising(error).get("/boom")

    assert response.status_code == status
    assert response.json() == {"detail": str(error)}


def test_non_domain_errors_are_not_handled():
    response = _client_raising(RuntimeError("bug")).get("/boom")

    assert response.status_code == 500
