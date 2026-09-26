import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from app.core.audio import Pcm, to_pcm, wav_bytes
from app.integrations.tts.uzbek import to_cyrillic

MARKDOWN = re.compile(r"[*_#`>|~]+")
FALLBACK_LANGUAGE = "en"


@dataclass(frozen=True, slots=True)
class Speech:
    wav: bytes
    language: str


class Speaker(Protocol):
    def load(self) -> None: ...

    def speak(self, text: str, language: str) -> Speech: ...


class Voice(Protocol):
    def load(self) -> None: ...

    def synthesize(self, text: str) -> tuple[Pcm, int]: ...


def clean_for_speech(text: str) -> str:
    return re.sub(r"\s+", " ", MARKDOWN.sub(" ", text)).strip()


class MmsVoice:
    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._model: object | None = None
        self._tokenizer: object | None = None

    def load(self) -> None:
        from transformers import AutoTokenizer, VitsModel

        self._model = VitsModel.from_pretrained(self._model_id)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_id)

    def synthesize(self, text: str) -> tuple[Pcm, int]:
        import torch

        assert self._model is not None
        assert self._tokenizer is not None
        inputs = self._tokenizer(to_cyrillic(text), return_tensors="pt")  # type: ignore[operator]
        with torch.no_grad():
            waveform = self._model(**inputs).waveform[0].numpy()  # type: ignore[operator]
        return to_pcm(waveform), int(self._model.config.sampling_rate)  # type: ignore[attr-defined]


class PiperSpeakerVoice:
    def __init__(self, name: str, models_dir: Path) -> None:
        self._name = name
        self._models_dir = models_dir
        self._voice: object | None = None

    def load(self) -> None:
        from piper import PiperVoice
        from piper.download_voices import download_voice

        self._models_dir.mkdir(parents=True, exist_ok=True)
        download_voice(self._name, self._models_dir)
        self._voice = PiperVoice.load(str(self._models_dir / f"{self._name}.onnx"))

    def synthesize(self, text: str) -> tuple[Pcm, int]:
        from piper import PiperVoice

        assert isinstance(self._voice, PiperVoice)
        chunks = list(self._voice.synthesize(text))
        if not chunks:
            return np.zeros(0, dtype=np.int16), self._voice.config.sample_rate
        pcm = np.concatenate([chunk.audio_int16_array for chunk in chunks]).astype(np.int16)
        return pcm, chunks[0].sample_rate


class LocalSpeaker:
    def __init__(self, voices: dict[str, Voice]) -> None:
        self._voices = voices

    def load(self) -> None:
        for voice in self._voices.values():
            voice.load()

    def speak(self, text: str, language: str) -> Speech:
        chosen = language if language in self._voices else FALLBACK_LANGUAGE
        pcm, sample_rate = self._voices[chosen].synthesize(clean_for_speech(text))
        return Speech(wav=wav_bytes(pcm, sample_rate), language=chosen)
