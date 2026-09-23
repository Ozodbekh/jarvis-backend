from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel

from app.core.exceptions import (
    AppError,
    ConflictError,
    ServiceUnavailableError,
    error_body,
    register_exception_handlers,
)


class Body(BaseModel):
    text: str


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("SOMETHING_BUSY", {"retry": True})

    @app.get("/unavailable")
    async def unavailable() -> None:
        raise ServiceUnavailableError("NOT_FOUND")

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected")

    @app.post("/echo")
    async def echo(body: Body) -> Body:
        return body

    return app


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=_build_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_app_error_answers_its_status_and_code(http: httpx.AsyncClient) -> None:
    response = await http.get("/conflict")

    assert response.status_code == 409
    assert response.json() == {"code": "SOMETHING_BUSY", "message": "The request failed.", "details": {"retry": True}}


async def test_known_code_gets_its_message(http: httpx.AsyncClient) -> None:
    response = await http.get("/unavailable")

    assert response.status_code == 503
    assert response.json()["message"] == "Not found."


async def test_validation_error_lists_the_fields(http: httpx.AsyncClient) -> None:
    response = await http.post("/echo", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["errors"][0]["loc"] == ["body", "text"]


async def test_unknown_route_is_not_found(http: httpx.AsyncClient) -> None:
    response = await http.get("/missing")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


async def test_wrong_method_is_not_allowed(http: httpx.AsyncClient) -> None:
    response = await http.post("/conflict")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"


async def test_unhandled_error_hides_the_cause(http: httpx.AsyncClient) -> None:
    response = await http.get("/boom")

    assert response.status_code == 500
    assert response.json() == error_body("INTERNAL_ERROR")
    assert "unexpected" not in response.text


def test_base_error_is_a_server_error() -> None:
    assert AppError.status_code == 500
    assert AppError("X").details == {}
