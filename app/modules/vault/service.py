from pathlib import Path

from app.modules.vault.constants import VAULT_REQUIRED_DIRS, VAULT_REQUIRED_FILES
from app.modules.vault.exceptions import VaultMissingError


class VaultService:
    def __init__(self, root: Path) -> None:
        self.root = root

    def missing(self) -> list[str]:
        if not self.root.is_dir():
            return [str(self.root)]
        missing_dirs = [name for name in VAULT_REQUIRED_DIRS if not (self.root / name).is_dir()]
        missing_files = [name for name in VAULT_REQUIRED_FILES if not (self.root / name).is_file()]
        return missing_dirs + missing_files

    def ensure_ready(self) -> None:
        if missing := self.missing():
            raise VaultMissingError("VAULT_MISSING", {"root": str(self.root), "missing": missing})
