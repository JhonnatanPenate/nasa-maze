import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.routers.deps import get_transport
from app.settings import Settings, get_settings


@pytest.fixture
def make_client():
    def _make(handler=None, **overrides) -> TestClient:
        app = create_app()
        settings = Settings(_env_file=None, **overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        if handler:
            app.dependency_overrides[get_transport] = lambda: httpx.MockTransport(handler)
        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client):
    return make_client()
