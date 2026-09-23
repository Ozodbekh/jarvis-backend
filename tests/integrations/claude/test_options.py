from app.core.config import Settings
from app.integrations.claude.options import SPOKEN_REPLY_RULES, build_options


def test_options_follow_the_brain_rules(settings: Settings) -> None:
    options = build_options(settings, session_id=None)

    assert options.cwd == settings.JARVIS_VAULT_DIR
    assert options.setting_sources == ["project"]
    assert options.skills == settings.BRAIN_SKILLS
    assert options.permission_mode == "dontAsk"
    assert options.allowed_tools == settings.BRAIN_ALLOWED_TOOLS
    assert options.include_partial_messages is True
    assert options.resume is None


def test_never_bypasses_permissions(settings: Settings) -> None:
    assert build_options(settings, None).permission_mode != "bypassPermissions"
    assert "Bash" not in build_options(settings, None).allowed_tools


def test_system_prompt_keeps_claude_code_and_appends_the_spoken_rules(settings: Settings) -> None:
    assert build_options(settings, None).system_prompt == {
        "type": "preset",
        "preset": "claude_code",
        "append": SPOKEN_REPLY_RULES,
    }


def test_resume_uses_the_stored_session(settings: Settings) -> None:
    assert build_options(settings, "abc-123").resume == "abc-123"


def test_model_and_effort_come_from_settings(settings: Settings) -> None:
    tuned = settings.model_copy(update={"BRAIN_MODEL": "sonnet", "BRAIN_EFFORT": "low"})

    options = build_options(tuned, None)

    assert options.model == "sonnet"
    assert options.effort == "low"


def test_options_do_not_share_lists_with_settings(settings: Settings) -> None:
    options = build_options(settings, None)
    options.allowed_tools.append("Bash")

    assert "Bash" not in settings.BRAIN_ALLOWED_TOOLS
