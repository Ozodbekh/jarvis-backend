import asyncio
from collections.abc import AsyncIterator

from app.integrations.claude.events import BrainEvent, Result, TextDelta
from app.integrations.claude.session import ClaudeUnavailableError


def result(text: str = "ok", *, session_id: str = "s1", num_turns: int = 1, is_error: bool = False) -> Result:
    return Result(
        text=text,
        session_id=session_id,
        is_error=is_error,
        subtype="error_during_execution" if is_error else "success",
        num_turns=num_turns,
        duration_ms=10,
        cost_usd=0.001,
    )


def reply(text: str, *, session_id: str = "s1", num_turns: int = 1) -> list[BrainEvent]:
    return [TextDelta(text), result(text, session_id=session_id, num_turns=num_turns)]


class FakeClaudeSession:
    def __init__(self) -> None:
        self.replies: list[list[BrainEvent]] = []
        self.prompts: list[str] = []
        self.starts: list[str | None] = []
        self.refuse_resume = False
        self.refuse_start = False
        self.fail_next_ask = False
        self.gate: asyncio.Event | None = None
        self.interrupts = 0
        self.stops = 0
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self, session_id: str | None) -> None:
        self.starts.append(session_id)
        if self.refuse_start or (session_id is not None and self.refuse_resume):
            self._running = False
            raise ClaudeUnavailableError("refused")
        self._running = True

    async def ask(self, prompt: str) -> AsyncIterator[BrainEvent]:
        self.prompts.append(prompt)
        if self.fail_next_ask:
            self.fail_next_ask = False
            raise ClaudeUnavailableError("cli died")
        events = self.replies.pop(0) if self.replies else reply("ok")
        for event in events:
            if self.gate is not None and isinstance(event, Result):
                await self.gate.wait()
            yield event

    async def interrupt(self) -> None:
        self.interrupts += 1

    async def stop(self) -> None:
        self.stops += 1
        self._running = False
