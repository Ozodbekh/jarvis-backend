from pathlib import Path

from app.modules.vault.constants import VAULT_REQUIRED_DIRS, VAULT_REQUIRED_FILES


def build_vault(root: Path) -> Path:
    for name in VAULT_REQUIRED_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    for name in VAULT_REQUIRED_FILES:
        (root / name).write_text("# JARVIS\n")
    return root
