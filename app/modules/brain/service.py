import asyncio
from collections.abc import AsyncIterator

from app.core.logging import get_logger
from app.integrations.claude.events import BrainEvent, Result
from app.integrations.claude.session import ClaudeSession, ClaudeUnavailableError
from app.modules.brain.exceptions import BrainBusyError, BrainFailedError, BrainUnavailableError
from app.modules.brain.state import BrainState, StateStore

logger = get_logger("app.brain")


class BrainService:
    def __init__(self, session: ClaudeSession, store: StateStore, max_turns: int) -> None:
        self._session = session
        self._store = store
        self._max_turns = max_turns
        self._state = BrainState()
        self._lock = asyncio.Lock()

    @property
    def session_id(self) -> str | None:
        return self._state.session_id

    @property
    def turns(self) -> int:
        return self._state.turns

    async def start(self) -> None:
        self._state = self._store.load()
        if self._state.session_id is None:
            await self._start_fresh()
            return
        try:
            await self._session.start(self._state.session_id)
        except ClaudeUnavailableError:
            logger.warning("resume_failed", session_id=self._state.session_id)
            await self._start_fresh()

    async def stop(self) -> None:
        await self._session.stop()

    async def run(self, text: str) -> AsyncIterator[BrainEvent]:
        if self._lock.locked():
            raise BrainBusyError("BRAIN_BUSY")
        async with self._lock:
            if self._should_rotate():
                await self._rotate()
            if not self._session.is_running:
                raise BrainUnavailableError("BRAIN_UNAVAILABLE")
            logger.info("command_started", turns=self._state.turns)
            logger.debug("command_text", text=text)
            finished = False
            try:
                async for event in self._session.ask(text):
                    if isinstance(event, Result):
                        self._record(event)
                    yield event
                finished = True
            except ClaudeUnavailableError as error:
                logger.warning("command_failed", reason=str(error))
                raise BrainUnavailableError("BRAIN_UNAVAILABLE") from error
            finally:
                if not finished:
                    await self._session.interrupt()

    async def run_to_end(self, text: str) -> Result:
        result: Result | None = None
        async for event in self.run(text):
            if isinstance(event, Result):
                result = event
        if result is None:
            raise BrainFailedError("BRAIN_FAILED", {"reason": "no_result"})
        return result

    def _record(self, result: Result) -> None:
        self._state = BrainState(session_id=result.session_id, turns=self._state.turns + result.num_turns)
        self._store.save(self._state)
        logger.info(
            "command_done",
            duration_ms=result.duration_ms,
            cost_usd=result.cost_usd,
            turns=self._state.turns,
            is_error=result.is_error,
        )
        logger.debug("command_reply", text=result.text)
        if result.is_error:
            raise BrainFailedError("BRAIN_FAILED", {"subtype": result.subtype})

    def _should_rotate(self) -> bool:
        return self._state.turns >= self._max_turns

    async def _rotate(self) -> None:
        logger.info("session_rotated", previous=self._state.session_id, turns=self._state.turns)
        await self._start_fresh()

    async def _start_fresh(self) -> None:
        self._state = BrainState()
        self._store.save(self._state)
        try:
            await self._session.start(None)
        except ClaudeUnavailableError as error:
            logger.error("claude_unavailable", reason=str(error))
            raise BrainUnavailableError("BRAIN_UNAVAILABLE") from error
