from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.claude.session import ClaudeSession, SdkClaudeSession
from app.modules.brain.service import BrainService
from app.modules.brain.state import StateStore
from app.modules.vault.exceptions import VaultMissingError
from app.modules.vault.service import VaultService

logger = get_logger("app.lifespan")

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def make_lifespan(settings: Settings, session: ClaudeSession | None = None) -> Lifespan:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        vault = VaultService(settings.JARVIS_VAULT_DIR)
        try:
            vault.ensure_ready()
        except VaultMissingError as error:
            logger.error("vault_missing", hint="run make vault", **error.details)
            raise

        brain = BrainService(
            session or SdkClaudeSession(settings),
            StateStore(settings.JARVIS_STATE_FILE),
            max_turns=settings.BRAIN_MAX_TURNS,
        )
        await brain.start()
        app.state.vault = vault
        app.state.brain = brain
        logger.info("jarvis_started", vault=str(vault.root), session_id=brain.session_id)
        try:
            yield
        finally:
            await brain.stop()
            logger.info("jarvis_stopped")

    return lifespan
