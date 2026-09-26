import numpy as np

from app.core.audio import SAMPLE_RATE, Pcm, wav_bytes
from app.integrations.stt.whisper import Transcript
from app.integrations.tts.speaker import Speech
from app.integrations.wakeword.detector import WAKE_CHUNK_SAMPLES
from app.modules.voice.service import VoiceEngines

LOUD = 3000


def chunk(amplitude: int = 0) -> bytes:
    return np.full(WAKE_CHUNK_SAMPLES, amplitude, dtype=np.int16).tobytes()


def audio(seconds: float, amplitude: int = 0) -> bytes:
    return np.full(int(SAMPLE_RATE * seconds), amplitude, dtype=np.int16).tobytes()


class FakeTranscriber:
    def __init__(self) -> None:
        self.transcripts: list[Transcript] = []
        self.heard: list[Pcm] = []
        self.languages: list[str | None] = []
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def transcribe(self, pcm: Pcm, language: str | None) -> Transcript:
        self.heard.append(pcm)
        self.languages.append(language)
        return self.transcripts.pop(0) if self.transcripts else Transcript("salom", "uz")


class FakeSpeaker:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def speak(self, text: str, language: str) -> Speech:
        self.spoken.append((text, language))
        return Speech(wav=wav_bytes(np.zeros(1600, dtype=np.int16), SAMPLE_RATE), language=language)


class FakeWakeWord:
    def __init__(self) -> None:
        self.trigger_on_loud = True
        self.resets = 0

    def feed(self, chunk: Pcm) -> bool:
        return self.trigger_on_loud and int(np.abs(chunk).max(initial=0)) >= LOUD

    def reset(self) -> None:
        self.resets += 1


def fake_engines() -> tuple[VoiceEngines, FakeTranscriber, FakeSpeaker, FakeWakeWord]:
    transcriber, speaker, wake = FakeTranscriber(), FakeSpeaker(), FakeWakeWord()
    return (
        VoiceEngines(transcriber=transcriber, speaker=speaker, new_wake_detector=lambda: wake),
        transcriber,
        speaker,
        wake,
    )
