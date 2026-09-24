import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.integrations.claude.events import BrainEvent, Result, TextDelta
from app.modules.brain.exceptions import BrainBusyError, BrainFailedError, BrainUnavailableError
from app.modules.brain.service import BrainService
from app.modules.brain.state import BrainState, StateStore
from tests.fakes.claude import FakeClaudeSession, reply, result


@pytest.fixture
def claude() -> FakeClaudeSession:
    return FakeClaudeSession()


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.json")


@pytest.fixture
async def brain(claude: FakeClaudeSession, store: StateStore) -> AsyncIterator[BrainService]:
    service = BrainService(claude, store, max_turns=5)
    await service.start()
    yield service
    await service.stop()


async def _collect(events: AsyncIterator[BrainEvent]) -> list[BrainEvent]:
    return [event async for event in events]


async def test_start_without_state_opens_a_fresh_session(brain: BrainService, claude: FakeClaudeSession) -> None:
    assert claude.starts == [None]
    assert brain.session_id is None


async def test_start_resumes_the_stored_session(claude: FakeClaudeSession, store: StateStore) -> None:
    store.save(BrainState(session_id="old", turns=2))
    service = BrainService(claude, store, max_turns=5)

    await service.start()

    assert claude.starts == ["old"]
    assert service.session_id == "old"
    assert service.turns == 2


async def test_failed_resume_falls_back_to_a_fresh_session(claude: FakeClaudeSession, store: StateStore) -> None:
    store.save(BrainState(session_id="gone", turns=2))
    claude.refuse_resume = True
    service = BrainService(claude, store, max_turns=5)

    await service.start()

    assert claude.starts == ["gone", None]
    assert store.load() == BrainState()


async def test_start_fails_when_claude_cannot_connect(claude: FakeClaudeSession, store: StateStore) -> None:
    claude.refuse_start = True

    with pytest.raises(BrainUnavailableError):
        await BrainService(claude, store, max_turns=5).start()


async def test_run_streams_events_and_records_the_session(
    brain: BrainService, claude: FakeClaudeSession, store: StateStore
) -> None:
    claude.replies.append(reply("Salom", session_id="s9", num_turns=2))

    events = await _collect(brain.run("salom"))

    assert events[0] == TextDelta("Salom")
    assert isinstance(events[1], Result)
    assert store.load() == BrainState(session_id="s9", turns=2)
    assert claude.prompts == ["salom"]


async def test_turns_accumulate_across_commands(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.replies += [reply("a", num_turns=1), reply("b", num_turns=3)]

    await _collect(brain.run("one"))
    await _collect(brain.run("two"))

    assert brain.turns == 4


async def test_second_command_while_busy_is_rejected(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.gate = asyncio.Event()
    first = asyncio.create_task(_collect(brain.run("slow")))
    await asyncio.sleep(0)

    with pytest.raises(BrainBusyError):
        await _collect(brain.run("fast"))

    claude.gate.set()
    await first
    assert claude.prompts == ["slow"]


async def test_error_result_raises_failed(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.replies.append([result("", is_error=True)])

    with pytest.raises(BrainFailedError) as caught:
        await _collect(brain.run("hi"))

    assert caught.value.details == {"subtype": "error_during_execution"}


async def test_lost_session_raises_unavailable(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.fail_next_ask = True

    with pytest.raises(BrainUnavailableError):
        await _collect(brain.run("hi"))


async def test_run_when_session_is_down_is_unavailable(brain: BrainService, claude: FakeClaudeSession) -> None:
    await claude.stop()

    with pytest.raises(BrainUnavailableError):
        await _collect(brain.run("hi"))


async def test_abandoned_command_interrupts_the_session(brain: BrainService, claude: FakeClaudeSession) -> None:
    events = brain.run("long")
    await anext(events)
    await events.aclose()

    assert claude.interrupts == 1


async def test_finished_command_does_not_interrupt(brain: BrainService, claude: FakeClaudeSession) -> None:
    await _collect(brain.run("hi"))

    assert claude.interrupts == 0


async def test_session_rotates_past_max_turns(
    brain: BrainService, claude: FakeClaudeSession, store: StateStore
) -> None:
    claude.replies += [reply("a", session_id="s1", num_turns=5), reply("b", session_id="s2", num_turns=1)]

    await _collect(brain.run("one"))
    await _collect(brain.run("two"))

    assert claude.starts == [None, None]
    assert store.load() == BrainState(session_id="s2", turns=1)


async def test_run_to_end_returns_the_result(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.replies.append(reply("Bugun uchta vazifa"))

    assert (await brain.run_to_end("plan")).text == "Bugun uchta vazifa"


async def test_run_to_end_without_a_result_fails(brain: BrainService, claude: FakeClaudeSession) -> None:
    claude.replies.append([TextDelta("half")])

    with pytest.raises(BrainFailedError):
        await brain.run_to_end("hi")
