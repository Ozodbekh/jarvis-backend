import io
import wave
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

TARGET_RATE = 16000
INT16_SCALE = 32768.0
INT32_SCALE = 2147483648.0


@dataclass(frozen=True, slots=True)
class WavAudio:
    frames: bytes
    sample_rate: int
    channels: int
    sample_width: int


def parse_wav(data: bytes) -> WavAudio:
    with wave.open(io.BytesIO(data)) as wav:
        return WavAudio(
            frames=wav.readframes(wav.getnframes()),
            sample_rate=wav.getframerate(),
            channels=wav.getnchannels(),
            sample_width=wav.getsampwidth(),
        )


def _to_float(data: bytes, sample_format: str) -> NDArray[np.float32]:
    match sample_format:
        case "int16":
            return (np.frombuffer(data, dtype=np.int16) / INT16_SCALE).astype(np.float32)
        case "int32":
            return (np.frombuffer(data, dtype=np.int32) / INT32_SCALE).astype(np.float32)
        case "float":
            return np.frombuffer(data, dtype=np.float32).astype(np.float32)
        case _:
            raise ValueError(sample_format)


def to_mono_16k(data: bytes, sample_rate: int, channels: int, sample_format: str) -> bytes:
    samples = _to_float(data, sample_format)
    usable = samples.size - samples.size % channels
    mono = samples[:usable].reshape(-1, channels).mean(axis=1)
    if sample_rate != TARGET_RATE and mono.size:
        positions = np.arange(0, mono.size, sample_rate / TARGET_RATE)
        mono = np.interp(positions, np.arange(mono.size), mono)
    return (np.clip(mono, -1.0, 1.0) * (INT16_SCALE - 1)).astype(np.int16).tobytes()


def level(data: bytes) -> float:
    samples = np.frombuffer(data[: len(data) - len(data) % 2], dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(min(1.0, np.sqrt(np.mean(samples.astype(np.float64) ** 2)) / 8000.0))
