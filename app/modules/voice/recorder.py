from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from app.core.audio import SAMPLE_RATE, Pcm, rms

NOISE_MULTIPLIER = 3.0
NOISE_SMOOTHING = 0.05


class RecorderStatus(StrEnum):
    RECORDING = "recording"
    DONE = "done"
    NOTHING_SAID = "nothing_said"


@dataclass(frozen=True, slots=True)
class Endpointing:
    min_speech_rms: int
    silence_ms: int
    start_timeout_ms: int
    max_utterance_s: int


@dataclass(slots=True)
class NoiseFloor:
    level: float = 0.0

    def observe(self, chunk: Pcm, minimum: int) -> None:
        energy = rms(chunk)
        if energy >= self.speech_threshold(minimum):
            return
        self.level = energy if self.level == 0.0 else self.level + NOISE_SMOOTHING * (energy - self.level)

    def speech_threshold(self, minimum: int) -> float:
        return max(float(minimum), self.level * NOISE_MULTIPLIER)


@dataclass(slots=True)
class UtteranceRecorder:
    endpointing: Endpointing
    threshold: float
    chunks: list[Pcm] = field(default_factory=list)
    heard_speech: bool = False
    silent_ms: float = 0.0
    elapsed_ms: float = 0.0

    def feed(self, chunk: Pcm) -> RecorderStatus:
        chunk_ms = 1000 * chunk.size / SAMPLE_RATE
        self.chunks.append(chunk)
        self.elapsed_ms += chunk_ms
        if rms(chunk) >= self.threshold:
            self.heard_speech = True
            self.silent_ms = 0.0
        else:
            self.silent_ms += chunk_ms

        if not self.heard_speech:
            timed_out = self.elapsed_ms >= self.endpointing.start_timeout_ms
            return RecorderStatus.NOTHING_SAID if timed_out else RecorderStatus.RECORDING
        if self.silent_ms >= self.endpointing.silence_ms:
            return RecorderStatus.DONE
        if self.elapsed_ms >= self.endpointing.max_utterance_s * 1000:
            return RecorderStatus.DONE
        return RecorderStatus.RECORDING

    def audio(self) -> Pcm:
        if not self.chunks:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(self.chunks).astype(np.int16)
