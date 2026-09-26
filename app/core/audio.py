import io
import wave

import numpy as np
from numpy.typing import NDArray

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
PCM_FULL_SCALE = 32767

type Pcm = NDArray[np.int16]


def pcm_from_bytes(data: bytes) -> Pcm:
    usable = len(data) - len(data) % SAMPLE_WIDTH
    pcm: Pcm = np.frombuffer(data[:usable], dtype=np.int16)
    return pcm


def rms(pcm: Pcm) -> float:
    if pcm.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(pcm.astype(np.float64) ** 2)))


def to_float(pcm: Pcm) -> NDArray[np.float32]:
    return (pcm.astype(np.float32) / (PCM_FULL_SCALE + 1)).astype(np.float32)


def to_pcm(audio: NDArray[np.floating]) -> Pcm:
    pcm: Pcm = (np.clip(audio, -1.0, 1.0) * PCM_FULL_SCALE).astype(np.int16)
    return pcm


def wav_bytes(pcm: Pcm, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(SAMPLE_WIDTH)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def wav_duration(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as wav:
        frames: int = wav.getnframes()
        rate: int = wav.getframerate()
    return frames / rate
