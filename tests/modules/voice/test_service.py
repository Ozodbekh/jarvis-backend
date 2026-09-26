import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.integrations.stt.whisper import Transcript
from app.modules.brain.service import BrainService
from app.modules.brain.state import StateStore
from app.modules.voice.recorder import Endpointing
from app.modules.voice.service import (
    Failed,
    Heard,
    Replied,
    Spoken,
    StateChanged,
    VoiceOutput,
    VoiceService,
    VoiceSession,
    VoiceState,
    reply_language,
)
from tests.fakes.claude import FakeClaudeSession, reply, result
from tests.fakes.voice import LOUD, FakeSpeaker, FakeTranscriber, FakeWakeWord, audio, chunk, fake_engines

ENDPOINTING = Endpointing(min_speech_rms=400, silence_ms=400, start_timeout_ms=1000, max_utterance_s=5)


class Harness:
    def __init__(self, session: VoiceSession, outputs: list[VoiceOutput]) -> None:
        self.session = session
        self.outputs = outputs

    def states(self) -> list[VoiceState]:
        return [output.state for output in self.outputs if isinstance(output, StateChanged)]

    async def settle(self) -> None:
        for _ in range(50):
            await asyncio.sleep(0.01)

    async def speak_command(self) -> None:
        await self.session.feed(audio(0.2, LOUD))
        await self.session.feed(audio(0.5, LOUD))
        await self.session.feed(audio(0.6))
        await self.settle()


@pytest.fixture
def claude() -> FakeClaudeSession:
    return FakeClaudeSession()


@pytest.fixture
async def brain(claude: FakeClaudeSession, tmp_path: Path) -> AsyncIterator[BrainService]:
    service = BrainService(claude, StateStore(tmp_path / "state.json"), max_turns=100)
    await service.start()
    yield service
    await service.stop()


@pytest.fixture
async def harness(brain: BrainService) -> AsyncIterator[tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord]]:
    voice_engines, transcriber, speaker, wake = fake_engines()
    outputs: list[VoiceOutput] = []

    async def send(output: VoiceOutput) -> None:
        outputs.append(output)

    session = VoiceService(voice_engines, brain, ENDPOINTING).open_session(send)
    yield Harness(session, outputs), transcriber, speaker, wake
    await session.close()


async def test_wake_word_command_is_heard_answered_and_spoken(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord], claude: FakeClaudeSession
) -> None:
    h, transcriber, speaker, _ = harness
    transcriber.transcripts.append(Transcript("Bugungi rejam nima?", "uz"))
    claude.replies.append(reply("Bugun uchta vazifa bor."))

    await h.speak_command()

    assert h.states() == [VoiceState.LISTENING, VoiceState.THINKING, VoiceState.SPEAKING]
    assert Heard("Bugungi rejam nima?", "uz") in h.outputs
    assert Replied("Bugun uchta vazifa bor.") in h.outputs
    assert any(isinstance(output, Spoken) for output in h.outputs)
    assert speaker.spoken == [("Bugun uchta vazifa bor.", "uz")]
    assert claude.prompts == ["Bugungi rejam nima?"]


async def test_played_returns_to_idle(harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord]) -> None:
    h, *_ = harness
    await h.speak_command()

    await h.session.played()

    assert h.session.state is VoiceState.IDLE


async def test_audio_is_ignored_while_thinking_or_speaking(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord],
) -> None:
    h, transcriber, *_ = harness
    await h.speak_command()

    await h.session.feed(audio(1.0, LOUD))
    await h.settle()

    assert len(transcriber.heard) == 1
    assert h.session.state is VoiceState.SPEAKING


async def test_silence_after_the_wake_word_goes_back_to_idle(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord],
) -> None:
    h, transcriber, *_ = harness
    await h.session.feed(chunk(LOUD))
    await h.session.feed(audio(1.2))

    assert h.states() == [VoiceState.LISTENING, VoiceState.IDLE]
    assert transcriber.heard == []


async def test_push_to_talk_starts_listening_without_the_wake_word(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord],
) -> None:
    h, transcriber, _, wake = harness
    wake.trigger_on_loud = False

    await h.session.listen()
    await h.session.feed(audio(0.5, LOUD))
    await h.session.feed(audio(0.6))
    await h.settle()

    assert h.states()[:2] == [VoiceState.LISTENING, VoiceState.THINKING]
    assert len(transcriber.heard) == 1


async def test_empty_transcript_returns_to_idle_without_asking_claude(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord], claude: FakeClaudeSession
) -> None:
    h, transcriber, *_ = harness
    transcriber.transcripts.append(Transcript("", "en"))

    await h.speak_command()

    assert h.states()[-1] is VoiceState.IDLE
    assert claude.prompts == []


async def test_failed_command_reports_and_returns_to_idle(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord], claude: FakeClaudeSession
) -> None:
    h, *_ = harness
    claude.replies.append([result("", is_error=True)])

    await h.speak_command()

    assert Failed("BRAIN_FAILED") in h.outputs
    assert h.states()[-1] is VoiceState.IDLE


async def test_speaking_times_out_to_idle_without_played(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.modules.voice.service.PLAYBACK_GRACE_S", 0.0)
    h, *_ = harness

    await h.speak_command()
    await h.settle()

    assert h.session.state is VoiceState.IDLE


@pytest.mark.parametrize(
    ("heard", "reply_text", "expected"),
    [
        ("en", "Привет, у вас встреча.", "ru"),
        ("en", "Payshanba kuni soat uchda uchrashuv bor.", "uz"),
        ("ru", "You have a meeting.", "ru"),
        ("en", "You have a meeting.", "en"),
        ("uz", "You have a meeting.", "en"),
    ],
)
def test_reply_language_follows_the_reply_text(heard: str, reply_text: str, expected: str) -> None:
    assert reply_language(heard, reply_text) == expected


async def test_chosen_language_is_passed_to_the_transcriber(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord],
) -> None:
    h, transcriber, *_ = harness

    h.session.set_language("uz")
    await h.speak_command()

    assert transcriber.languages == ["uz"]


async def test_auto_language_lets_the_transcriber_decide(
    harness: tuple[Harness, FakeTranscriber, FakeSpeaker, FakeWakeWord],
) -> None:
    h, transcriber, *_ = harness

    await h.speak_command()

    assert transcriber.languages == [None]
