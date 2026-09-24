from app.modules.vault.constants import VAULT_REQUIRED_DIRS, VAULT_REQUIRED_FILES


def test_layout_matches_the_documented_vault() -> None:
    assert set(VAULT_REQUIRED_DIRS) == {"raw", "wiki", "outputs", ".claude/skills"}
    assert VAULT_REQUIRED_FILES == ("CLAUDE.md",)
