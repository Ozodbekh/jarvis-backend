import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum

import anyio

from app.core.audio import Pcm, pcm_from_bytes, wav_duration
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.integrations.stt.whisper import Transcriber
from app.integrations.tts.speaker import Speaker
from app.integrations.tts.uzbek import has_cyrillic, looks_uzbek
from app.integrations.wakeword.detector import WAKE_CHUNK_SAMPLES, WakeWordDetector
from app.modules.brain.service import BrainService
from app.modules.voice.recorder import Endpointing, NoiseFloor, RecorderStatus, UtteranceRecorder

logger = get_logger("app.voice")

CHUNK_BYTES = WAKE_CHUNK_SAMPLES * 2
PLAYBACK_GRACE_S = 3.0


class VoiceState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


@dataclass(frozen=True, slots=True)
class StateChanged:
    state: VoiceState


@dataclass(frozen=True, slots=True)
class Heard:
    text: str
    language: str


@dataclass(frozen=True, slots=True)
class Replied:
    text: str


@dataclass(frozen=True, slots=True)
class Spoken:
    wav: bytes


@dataclass(frozen=True, slots=True)
class Failed:
    code: str


type VoiceOutput = StateChanged | Heard | Replied | Spoken | Failed
type Send = Callable[[VoiceOutput], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class VoiceEngines:
    transcriber: Transcriber
    speaker: Speaker
    new_wake_detector: Callable[[], WakeWordDetector]

    def load(self) -> None:
        self.transcriber.load()
        self.speaker.load()


def reply_language(heard_language: str, reply: str) -> str:
    if has_cyrillic(reply):
        return "ru"
    if looks_uzbek(reply):
        return "uz"
    return "en" if heard_language == "uz" else heard_language


class VoiceSession:
    def __init__(self, engines: VoiceEngines, brain: BrainService, endpointing: Endpointing, send: Send) -> None:
        self._engines = engines
        self._brain = brain
        self._endpointing = endpointing
        self._send = send
        self._wake = engines.new_wake_detector()
        self._noise = NoiseFloor()
        self._buffer = b""
        self._recorder: UtteranceRecorder | None = None
        self._task: asyncio.Task[None] | None = None
        self.state = VoiceState.IDLE
        self.language: str | None = None

    async def feed(self, data: bytes) -> None:
        self._buffer += data
        while len(self._buffer) >= CHUNK_BYTES:
            chunk = pcm_from_bytes(self._buffer[:CHUNK_BYTES])
            self._buffer = self._buffer[CHUNK_BYTES:]
            await self._feed_chunk(chunk)

    async def listen(self) -> None:
        if self.state is VoiceState.IDLE:
            await self._start_listening()

    def set_language(self, language: str | None) -> None:
        self.language = language
        logger.info("voice_language_set", language=language or "auto")

    async def played(self) -> None:
        if self.state is VoiceState.SPEAKING:
            await self._set_state(VoiceState.IDLE)

    async def close(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _feed_chunk(self, chunk: Pcm) -> None:
        if self.state is VoiceState.IDLE:
            self._noise.observe(chunk, self._endpointing.min_speech_rms)
            if self._wake.feed(chunk):
                logger.info("wake_word_heard")
                await self._start_listening()
        elif self.state is VoiceState.LISTENING and self._recorder is not None:
            status = self._recorder.feed(chunk)
            if status is RecorderStatus.NOTHING_SAID:
                self._recorder = None
                await self._set_state(VoiceState.IDLE)
            elif status is RecorderStatus.DONE:
                audio = self._recorder.audio()
                self._recorder = None
                await self._set_state(VoiceState.THINKING)
                self._task = asyncio.create_task(self._respond(audio))

    async def _start_listening(self) -> None:
        self._wake.reset()
        threshold = self._noise.speech_threshold(self._endpointing.min_speech_rms)
        self._recorder = UtteranceRecorder(self._endpointing, threshold)
        await self._set_state(VoiceState.LISTENING)

    async def _set_state(self, state: VoiceState) -> None:
        self.state = state
        if state is VoiceState.IDLE:
            self._wake.reset()
        await self._send(StateChanged(state))

    async def _respond(self, audio: Pcm) -> None:
        try:
            transcript = await anyio.to_thread.run_sync(self._engines.transcriber.transcribe, audio, self.language)
            if not transcript.text:
                await self._set_state(VoiceState.IDLE)
                return
            await self._send(Heard(transcript.text, transcript.language))
            result = await self._brain.run_to_end(transcript.text)
            await self._send(Replied(result.text))
            language = reply_language(transcript.language, result.text)
            speech = await anyio.to_thread.run_sync(self._engines.speaker.speak, result.text, language)
            await self._set_state(VoiceState.SPEAKING)
            await self._send(Spoken(speech.wav))
            self._task = asyncio.create_task(self._return_to_idle_after(wav_duration(speech.wav) + PLAYBACK_GRACE_S))
        except AppError as error:
            await self._send(Failed(error.code))
            await self._set_state(VoiceState.IDLE)
        except Exception:
            logger.exception("voice_response_failed")
            await self._send(Failed("INTERNAL_ERROR"))
            await self._set_state(VoiceState.IDLE)

    async def _return_to_idle_after(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
        if self.state is VoiceState.SPEAKING:
            await self._set_state(VoiceState.IDLE)


class VoiceService:
    def __init__(self, engines: VoiceEngines, brain: BrainService, endpointing: Endpointing) -> None:
        self._engines = engines
        self._brain = brain
        self._endpointing = endpointing

    def open_session(self, send: Send) -> VoiceSession:
        return VoiceSession(self._engines, self._brain, self._endpointing, send)
