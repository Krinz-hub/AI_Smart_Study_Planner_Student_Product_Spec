import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.common.config import get_settings

settings = get_settings()
settings.APP_ENV = "testing"


@pytest_asyncio.fixture
async def app_instance():
    app = create_app()
    return app


@pytest_asyncio.fixture
async def async_client(app_instance):
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
