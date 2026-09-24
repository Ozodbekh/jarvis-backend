import re
from pathlib import Path

import pytest

from app.core.config import DEFAULT_SKILLS
from app.modules.vault.service import VaultService
from scripts.init_vault import TEMPLATE_DIR, init_vault, main

FRONTMATTER = re.compile(r"\A---\nname: (?P<name>[a-z-]+)\ndescription: (?P<description>.+)\n---\n")


def test_fresh_vault_passes_the_startup_check(tmp_path: Path) -> None:
    vault = tmp_path / "vault"

    report = init_vault(vault)

    VaultService(vault).ensure_ready()
    assert "CLAUDE.md" in report.copied
    assert ".claude/skills/plan/SKILL.md" in report.copied
    assert report.kept == []


def test_template_names_are_mapped_to_what_claude_code_reads(tmp_path: Path) -> None:
    vault = tmp_path / "vault"

    init_vault(vault)

    assert (vault / "CLAUDE.md").read_text() == (TEMPLATE_DIR / "JARVIS.md").read_text()
    assert not (vault / "JARVIS.md").exists()
    assert not (vault / "skills").exists()


def test_existing_files_are_kept(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    init_vault(vault)
    (vault / "CLAUDE.md").write_text("edited by the owner")

    report = init_vault(vault)

    assert (vault / "CLAUDE.md").read_text() == "edited by the owner"
    assert "CLAUDE.md" in report.kept
    assert report.copied == []
    assert report.created_dirs == []


def test_force_overwrites_template_files_only(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    init_vault(vault)
    (vault / "CLAUDE.md").write_text("edited by the owner")
    (vault / "wiki" / "note.md").write_text("owner's note")

    init_vault(vault, force=True)

    assert (vault / "CLAUDE.md").read_text() == (TEMPLATE_DIR / "JARVIS.md").read_text()
    assert (vault / "wiki" / "note.md").read_text() == "owner's note"


def test_main_uses_the_given_vault(tmp_path: Path) -> None:
    report = main(["--vault", str(tmp_path / "v")])

    assert (tmp_path / "v" / "CLAUDE.md").is_file()
    assert "raw" in report.created_dirs


def test_template_skills_are_exactly_the_enabled_skills() -> None:
    names = sorted(path.name for path in (TEMPLATE_DIR / "skills").iterdir() if path.is_dir())

    assert names == sorted(DEFAULT_SKILLS)


@pytest.mark.parametrize("skill", DEFAULT_SKILLS)
def test_each_skill_has_frontmatter_naming_it(skill: str) -> None:
    text = (TEMPLATE_DIR / "skills" / skill / "SKILL.md").read_text()

    match = FRONTMATTER.match(text)

    assert match is not None
    assert match["name"] == skill
    assert len(match["description"]) > 40


def test_template_uses_no_name_claude_code_would_load_in_this_repository() -> None:
    assert not (TEMPLATE_DIR / "CLAUDE.md").exists()
    assert not (TEMPLATE_DIR / ".claude").exists()
