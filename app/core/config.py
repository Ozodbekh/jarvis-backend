from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

CsvList = Annotated[list[str], NoDecode]
EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]

DEFAULT_SKILLS = ["metrics", "inbox", "trends", "plan", "vault"]
DEFAULT_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Skill"]
DEFAULT_MAX_TURNS = 100
DEFAULT_VOICE_LANGUAGES = ["uz", "ru", "en"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    DEBUG: bool = False
    LOG_LEVEL: str | None = None

    JARVIS_VAULT_DIR: Path = Path("~/jarvis-vault")
    JARVIS_STATE_FILE: Path = Path("data/state.json")

    BRAIN_MODEL: str | None = None
    BRAIN_EFFORT: EffortLevel | None = None
    BRAIN_SKILLS: CsvList = Field(default_factory=lambda: list(DEFAULT_SKILLS))
    BRAIN_ALLOWED_TOOLS: CsvList = Field(default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS))
    BRAIN_MAX_TURNS: int = Field(default=DEFAULT_MAX_TURNS, gt=0)

    VOICE_ENABLED: bool = True
    VOICE_MODELS_DIR: Path = Path("data/voices")
    VOICE_LANGUAGES: CsvList = Field(default_factory=lambda: list(DEFAULT_VOICE_LANGUAGES))
    VOICE_STT_MODEL: str = "small"
    VOICE_STT_UZ_SOURCE: str = "OvozifyLabs/whisper-small-uz-v1"
    VOICE_STT_UZ_DIR: Path = Path("data/models/whisper-small-uz")
    VOICE_WAKE_THRESHOLD: float = Field(default=0.5, gt=0, lt=1)
    VOICE_TTS_UZ: str = "facebook/mms-tts-uzb-script_cyrillic"
    VOICE_TTS_RU: str = "ru_RU-irina-medium"
    VOICE_TTS_EN: str = "en_US-amy-medium"
    VOICE_MIN_SPEECH_RMS: int = Field(default=400, gt=0)
    VOICE_SILENCE_MS: int = Field(default=800, gt=0)
    VOICE_START_TIMEOUT_MS: int = Field(default=5000, gt=0)
    VOICE_MAX_UTTERANCE_S: int = Field(default=15, gt=0)

    @field_validator("BRAIN_SKILLS", "BRAIN_ALLOWED_TOOLS", "VOICE_LANGUAGES", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("JARVIS_VAULT_DIR", "JARVIS_STATE_FILE", "VOICE_MODELS_DIR", "VOICE_STT_UZ_DIR", mode="after")
    @classmethod
    def _resolve_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @property
    def log_level(self) -> str:
        if self.LOG_LEVEL:
            return self.LOG_LEVEL.upper()
        return "DEBUG" if self.DEBUG else "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
