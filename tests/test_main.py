from pathlib import Path

import httpx
from fastapi import FastAPI

from app.core.config import Settings
from app.main import create_app


async def test_health_answers_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_docs_are_hidden_outside_debug(client: httpx.AsyncClient) -> None:
    assert (await client.get("/docs")).status_code == 404
    assert (await client.get("/openapi.json")).status_code == 404


async def test_docs_are_served_in_debug(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, DEBUG=True, JARVIS_VAULT_DIR=tmp_path))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        assert (await http.get("/docs")).status_code == 200


async def test_health_is_not_in_the_schema(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, DEBUG=True, JARVIS_VAULT_DIR=tmp_path))

    assert "/health" not in app.openapi()["paths"]


def test_settings_are_kept_on_the_app(app: FastAPI, settings: Settings) -> None:
    assert app.state.settings is settings
