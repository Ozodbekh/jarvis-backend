from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from app.core.audio import Pcm, to_float

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_BEAM_SIZE = 5
UZBEK = "uz"
CT2_COPY_FILES = ["tokenizer_config.json", "preprocessor_config.json"]


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    language: str


class Transcriber(Protocol):
    def load(self) -> None: ...

    def transcribe(self, pcm: Pcm, language: str | None) -> Transcript: ...


def pick_language(probabilities: list[tuple[str, float]], allowed: list[str]) -> str:
    table = dict(probabilities)
    return max(allowed, key=lambda code: table.get(code, 0.0))


def uses_uzbek_model(language: str, has_uzbek_model: bool) -> bool:
    return language == UZBEK and has_uzbek_model


def ensure_ct2_model(source: str, target: Path) -> Path:
    if (target / "model.bin").is_file():
        return target
    from ctranslate2.converters import TransformersConverter

    target.parent.mkdir(parents=True, exist_ok=True)
    TransformersConverter(source, copy_files=CT2_COPY_FILES).convert(str(target), quantization=WHISPER_COMPUTE_TYPE)
    return target


class WhisperTranscriber:
    def __init__(self, model_size: str, languages: list[str], uzbek_source: str, uzbek_dir: Path) -> None:
        self._model_size = model_size
        self._languages = list(languages)
        self._uzbek_source = uzbek_source
        self._uzbek_dir = uzbek_dir
        self._general: WhisperModel | None = None
        self._uzbek: WhisperModel | None = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        self._general = WhisperModel(self._model_size, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        if UZBEK in self._languages and self._uzbek_source:
            path = ensure_ct2_model(self._uzbek_source, self._uzbek_dir)
            self._uzbek = WhisperModel(str(path), device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)

    def transcribe(self, pcm: Pcm, language: str | None) -> Transcript:
        assert self._general is not None
        audio = to_float(pcm)
        if language is None:
            _, _, probabilities = self._general.detect_language(audio)
            language = pick_language(probabilities, self._languages)
        model = self._uzbek if uses_uzbek_model(language, self._uzbek is not None) else self._general
        assert model is not None
        segments, _ = model.transcribe(audio, language=language, beam_size=WHISPER_BEAM_SIZE, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return Transcript(text=text, language=language)
