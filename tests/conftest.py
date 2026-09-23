import os

os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        JARVIS_VAULT_DIR=tmp_path / "vault",
        JARVIS_STATE_FILE=tmp_path / "data" / "state.json",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
