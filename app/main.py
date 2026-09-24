from typing import Literal

from fastapi import FastAPI

from app.common.schemas import ResponseSchema
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.integrations.claude.session import ClaudeSession
from app.lifespan import make_lifespan


class HealthResponse(ResponseSchema):
    status: Literal["ok"]


async def health() -> HealthResponse:
    return HealthResponse(status="ok")


def create_app(settings: Settings | None = None, claude_session: ClaudeSession | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="JARVIS",
        lifespan=make_lifespan(settings, claude_session),
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )
    app.state.settings = settings
    register_exception_handlers(app)
    app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
