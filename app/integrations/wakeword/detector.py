from typing import Protocol

from app.core.audio import Pcm

WAKE_WORD_MODEL = "hey_jarvis"
WAKE_CHUNK_SAMPLES = 1280


class WakeWordDetector(Protocol):
    def feed(self, chunk: Pcm) -> bool: ...

    def reset(self) -> None: ...


class OpenWakeWordDetector:
    def __init__(self, threshold: float) -> None:
        import openwakeword
        from openwakeword.model import Model

        paths = [path for path in openwakeword.get_pretrained_model_paths() if WAKE_WORD_MODEL in path]
        self._model = Model(wakeword_model_paths=paths)
        self._threshold = threshold

    def feed(self, chunk: Pcm) -> bool:
        scores = self._model.predict(chunk)
        return max(scores.values(), default=0.0) >= self._threshold

    def reset(self) -> None:
        self._model.reset()
