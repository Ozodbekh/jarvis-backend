from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

import anyio
from fastapi import FastAPI

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.claude.session import ClaudeSession, SdkClaudeSession
from app.integrations.stt.whisper import WhisperTranscriber
from app.integrations.tts.speaker import LocalSpeaker, MmsVoice, PiperSpeakerVoice
from app.integrations.wakeword.detector import OpenWakeWordDetector
from app.modules.brain.service import BrainService
from app.modules.brain.state import StateStore
from app.modules.vault.exceptions import VaultMissingError
from app.modules.vault.service import VaultService
from app.modules.voice.recorder import Endpointing
from app.modules.voice.service import VoiceEngines, VoiceService

logger = get_logger("app.lifespan")

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def build_local_voice(settings: Settings) -> VoiceEngines:
    speaker = LocalSpeaker(
        {
            "uz": MmsVoice(settings.VOICE_TTS_UZ),
            "ru": PiperSpeakerVoice(settings.VOICE_TTS_RU, settings.VOICE_MODELS_DIR),
            "en": PiperSpeakerVoice(settings.VOICE_TTS_EN, settings.VOICE_MODELS_DIR),
        }
    )
    return VoiceEngines(
        transcriber=WhisperTranscriber(
            settings.VOICE_STT_MODEL,
            settings.VOICE_LANGUAGES,
            settings.VOICE_STT_UZ_SOURCE,
            settings.VOICE_STT_UZ_DIR,
        ),
        speaker=speaker,
        new_wake_detector=lambda: OpenWakeWordDetector(settings.VOICE_WAKE_THRESHOLD),
    )


def endpointing(settings: Settings) -> Endpointing:
    return Endpointing(
        min_speech_rms=settings.VOICE_MIN_SPEECH_RMS,
        silence_ms=settings.VOICE_SILENCE_MS,
        start_timeout_ms=settings.VOICE_START_TIMEOUT_MS,
        max_utterance_s=settings.VOICE_MAX_UTTERANCE_S,
    )


def make_lifespan(
    settings: Settings,
    session: ClaudeSession | None = None,
    voice: VoiceEngines | None = None,
) -> Lifespan:
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

        if voice is not None or settings.VOICE_ENABLED:
            engines = voice or build_local_voice(settings)
            if voice is None:
                logger.info("voice_loading", stt=settings.VOICE_STT_MODEL)
                await anyio.to_thread.run_sync(engines.load)
            app.state.voice = VoiceService(engines, brain, endpointing(settings))
            logger.info("voice_ready")

        logger.info("jarvis_started", vault=str(vault.root), session_id=brain.session_id)
        try:
            yield
        finally:
            await brain.stop()
            logger.info("jarvis_stopped")

    return lifespan
