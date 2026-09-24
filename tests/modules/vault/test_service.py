from pathlib import Path

import pytest

from app.modules.vault.exceptions import VaultMissingError
from app.modules.vault.service import VaultService
from tests.fakes.vault import build_vault


def test_complete_vault_is_ready(tmp_path: Path) -> None:
    service = VaultService(build_vault(tmp_path / "vault"))

    assert service.missing() == []
    service.ensure_ready()


def test_absent_root_is_reported_as_the_root(tmp_path: Path) -> None:
    root = tmp_path / "nowhere"

    assert VaultService(root).missing() == [str(root)]


def test_each_missing_part_is_named(tmp_path: Path) -> None:
    root = build_vault(tmp_path / "vault")
    (root / "wiki").rmdir()
    (root / "CLAUDE.md").unlink()

    assert VaultService(root).missing() == ["wiki", "CLAUDE.md"]


def test_ensure_ready_raises_with_the_missing_parts(tmp_path: Path) -> None:
    root = build_vault(tmp_path / "vault")
    (root / "outputs").rmdir()

    with pytest.raises(VaultMissingError) as caught:
        VaultService(root).ensure_ready()

    assert caught.value.code == "VAULT_MISSING"
    assert caught.value.status_code == 503
    assert caught.value.details == {"root": str(root), "missing": ["outputs"]}
