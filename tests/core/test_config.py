from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_ALLOWED_TOOLS, DEFAULT_MAX_TURNS, DEFAULT_SKILLS, Settings


def test_defaults_match_the_documented_brain() -> None:
    settings = Settings(_env_file=None)

    assert settings.BRAIN_SKILLS == DEFAULT_SKILLS
    assert settings.BRAIN_ALLOWED_TOOLS == DEFAULT_ALLOWED_TOOLS
    assert "Bash" not in settings.BRAIN_ALLOWED_TOOLS
    assert settings.BRAIN_MAX_TURNS == DEFAULT_MAX_TURNS
    assert settings.BRAIN_MODEL is None
    assert settings.BRAIN_EFFORT is None


def test_csv_lists_are_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAIN_SKILLS", " plan, vault,, ")
    monkeypatch.setenv("BRAIN_ALLOWED_TOOLS", "Read,Grep")

    settings = Settings(_env_file=None)

    assert settings.BRAIN_SKILLS == ["plan", "vault"]
    assert settings.BRAIN_ALLOWED_TOOLS == ["Read", "Grep"]


def test_empty_variables_mean_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAIN_MODEL", "")
    monkeypatch.setenv("BRAIN_EFFORT", "")

    settings = Settings(_env_file=None)

    assert settings.BRAIN_MODEL is None
    assert settings.BRAIN_EFFORT is None


def test_paths_are_expanded_and_absolute() -> None:
    settings = Settings(_env_file=None, JARVIS_VAULT_DIR="~/some-vault", JARVIS_STATE_FILE="data/state.json")

    assert Path.home() / "some-vault" == settings.JARVIS_VAULT_DIR
    assert settings.JARVIS_STATE_FILE.is_absolute()


@pytest.mark.parametrize(
    ("debug", "log_level", "expected"),
    [(True, None, "DEBUG"), (False, None, "INFO"), (False, "warning", "WARNING")],
)
def test_log_level_follows_debug_unless_set(
    monkeypatch: pytest.MonkeyPatch, debug: bool, log_level: str | None, expected: str
) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None, DEBUG=debug, LOG_LEVEL=log_level)

    assert settings.log_level == expected


def test_unknown_effort_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, BRAIN_EFFORT="extreme")


def test_max_turns_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, BRAIN_MAX_TURNS=0)
