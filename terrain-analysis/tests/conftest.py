import pytest

from app.core.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()
