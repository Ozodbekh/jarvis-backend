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

    @field_validator("BRAIN_SKILLS", "BRAIN_ALLOWED_TOOLS", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("JARVIS_VAULT_DIR", "JARVIS_STATE_FILE", mode="after")
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
