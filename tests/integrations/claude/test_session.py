import asyncio
from collections.abc import AsyncIterator

import pytest
from claude_agent_sdk import ClaudeAgentOptions, CLIConnectionError, Message, ProcessError, ResultMessage, StreamEvent

from app.core.config import Settings
from app.integrations.claude.events import BrainEvent, Result, TextDelta
from app.integrations.claude.session import ClaudeUnavailableError, SdkClaudeSession


def _delta(text: str) -> StreamEvent:
    return StreamEvent(
        uuid="u", session_id="s1", event={"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}
    )


def _result(text: str) -> ResultMessage:
    return ResultMessage(
        subtype="success", duration_ms=5, duration_api_ms=4, is_error=False, num_turns=1, session_id="s1", result=text
    )


class FakeSdkClient:
    def __init__(self, options: ClaudeAgentOptions) -> None:
        self.options = options
        self.prompts: list[str] = []
        self.replies: list[list[Message]] = []
        self.connect_error: Exception | None = None
        self.receive_error: Exception | None = None
        self.connected = False
        self.interrupted = 0
        self.connect_task: asyncio.Task[object] | None = None
        self.disconnect_task: asyncio.Task[object] | None = None

    async def connect(self) -> None:
        self.connect_task = asyncio.current_task()
        if self.connect_error:
            raise self.connect_error
        self.connected = True

    async def query(self, prompt: str) -> None:
        self.prompts.append(prompt)

    async def receive_response(self) -> AsyncIterator[Message]:
        if self.receive_error:
            raise self.receive_error
        for message in self.replies.pop(0):
            yield message

    async def interrupt(self) -> None:
        self.interrupted += 1

    async def disconnect(self) -> None:
        self.disconnect_task = asyncio.current_task()
        self.connected = False


class Factory:
    def __init__(self) -> None:
        self.clients: list[FakeSdkClient] = []
        self.connect_error: Exception | None = None

    def __call__(self, options: ClaudeAgentOptions) -> FakeSdkClient:
        client = FakeSdkClient(options)
        client.connect_error = self.connect_error
        self.clients.append(client)
        return client


async def _collect(events: AsyncIterator[BrainEvent]) -> list[BrainEvent]:
    return [event async for event in events]


@pytest.fixture
def factory() -> Factory:
    return Factory()


@pytest.fixture
def session(settings: Settings, factory: Factory) -> SdkClaudeSession:
    return SdkClaudeSession(settings, client_factory=factory)


async def test_ask_streams_deltas_then_the_result(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start(None)
    factory.clients[0].replies.append([_delta("Sa"), _delta("lom"), _result("Salom")])

    events = await _collect(session.ask("salom"))
    await session.stop()

    assert factory.clients[0].prompts == ["salom"]
    assert events[:2] == [TextDelta("Sa"), TextDelta("lom")]
    assert isinstance(events[2], Result)
    assert events[2].text == "Salom"


async def test_client_lives_in_one_task_from_connect_to_disconnect(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start(None)
    factory.clients[0].replies.append([_result("ok")])
    await _collect(session.ask("hi"))
    await session.stop()

    client = factory.clients[0]
    assert client.connect_task is not None
    assert client.connect_task is client.disconnect_task
    assert client.connect_task is not asyncio.current_task()
    assert not client.connected


async def test_start_resumes_the_given_session(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start("old-session")
    await session.stop()

    assert factory.clients[0].options.resume == "old-session"


async def test_restart_replaces_the_client(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start("old")
    await session.start(None)
    await session.stop()

    assert len(factory.clients) == 2
    assert not factory.clients[0].connected
    assert factory.clients[1].options.resume is None


async def test_connect_failure_is_unavailable(session: SdkClaudeSession, factory: Factory) -> None:
    factory.connect_error = CLIConnectionError("no claude")

    with pytest.raises(ClaudeUnavailableError):
        await session.start(None)

    assert not session.is_running


async def test_ask_before_start_is_unavailable(session: SdkClaudeSession) -> None:
    with pytest.raises(ClaudeUnavailableError):
        await _collect(session.ask("hi"))


async def test_failed_request_raises_and_keeps_the_session(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start(None)
    client = factory.clients[0]
    client.receive_error = ProcessError("cli died", exit_code=1)

    with pytest.raises(ClaudeUnavailableError):
        await _collect(session.ask("hi"))

    client.receive_error = None
    client.replies.append([_result("back")])
    events = await _collect(session.ask("again"))
    await session.stop()

    assert isinstance(events[-1], Result)


async def test_stop_interrupts_first(session: SdkClaudeSession, factory: Factory) -> None:
    await session.start(None)
    await session.stop()

    assert factory.clients[0].interrupted == 1
    assert not session.is_running


async def test_interrupt_without_a_client_does_nothing(session: SdkClaudeSession) -> None:
    await session.interrupt()
    await session.stop()


@pytest.mark.live
async def test_live_session_answers_and_resumes(settings: Settings) -> None:
    settings.JARVIS_VAULT_DIR.mkdir(parents=True)
    live = SdkClaudeSession(settings.model_copy(update={"BRAIN_SKILLS": [], "BRAIN_EFFORT": "low"}))

    await live.start(None)
    first = await _collect(live.ask("Reply with exactly the word: OK"))
    await live.stop()

    [result] = [event for event in first if isinstance(event, Result)]
    assert not result.is_error
    assert "OK" in result.text

    await live.start(result.session_id)
    second = await _collect(live.ask("What single word did you reply with last time? Reply with just that word."))
    await live.stop()

    [resumed] = [event for event in second if isinstance(event, Result)]
    assert "OK" in resumed.text
