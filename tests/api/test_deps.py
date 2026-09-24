import httpx
from fastapi import FastAPI

from app.api.deps import Brain
from app.core.exceptions import register_exception_handlers


async def test_missing_brain_is_unavailable() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/probe")
    async def probe(brain: Brain) -> None:
        return None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/probe")

    assert response.status_code == 503
    assert response.json()["code"] == "BRAIN_UNAVAILABLE"
