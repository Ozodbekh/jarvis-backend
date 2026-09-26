from pathlib import Path

import pytest

from app.core.config import Settings
from app.main import create_app
from app.modules.brain.service import BrainService
from app.modules.brain.state import BrainState, StateStore
from app.modules.vault.exceptions import VaultMissingError
from app.modules.vault.service import VaultService
from tests.fakes.claude import FakeClaudeSession
from tests.fakes.vault import build_vault


async def test_startup_checks_the_vault_and_starts_the_brain(settings: Settings) -> None:
    build_vault(settings.JARVIS_VAULT_DIR)
    claude = FakeClaudeSession()
    app = create_app(settings, claude_session=claude)

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.vault, VaultService)
        assert isinstance(app.state.brain, BrainService)
        assert claude.is_running

    assert claude.stops == 1


async def test_startup_resumes_the_stored_session(settings: Settings) -> None:
    build_vault(settings.JARVIS_VAULT_DIR)
    StateStore(settings.JARVIS_STATE_FILE).save(BrainState(session_id="kept", turns=3))
    claude = FakeClaudeSession()
    app = create_app(settings, claude_session=claude)

    async with app.router.lifespan_context(app):
        assert claude.starts == ["kept"]


async def test_startup_refuses_without_a_vault(settings: Settings, tmp_path: Path) -> None:
    claude = FakeClaudeSession()
    app = create_app(settings, claude_session=claude)

    with pytest.raises(VaultMissingError):
        async with app.router.lifespan_context(app):
            pass

    assert claude.starts == []


async def test_startup_loads_voice_when_given_engines(settings: Settings) -> None:
    from app.modules.voice.service import VoiceService
    from tests.fakes.voice import fake_engines

    build_vault(settings.JARVIS_VAULT_DIR)
    engines, *_ = fake_engines()
    app = create_app(settings, claude_session=FakeClaudeSession(), voice_engines=engines)

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.voice, VoiceService)


async def test_voice_is_absent_when_turned_off(settings: Settings) -> None:
    build_vault(settings.JARVIS_VAULT_DIR)
    app = create_app(settings, claude_session=FakeClaudeSession())

    async with app.router.lifespan_context(app):
        assert not hasattr(app.state, "voice")
