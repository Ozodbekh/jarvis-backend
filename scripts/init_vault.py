import argparse
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger
from app.modules.vault.constants import VAULT_REQUIRED_DIRS

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "vault_template"
TEMPLATE_TARGETS = {Path("JARVIS.md"): Path("CLAUDE.md"), Path("skills"): Path(".claude/skills")}

logger = get_logger("app.scripts.init_vault")


@dataclass
class InitReport:
    created_dirs: list[str] = field(default_factory=list)
    copied: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)


def _target_for(relative: Path) -> Path:
    for source, target in TEMPLATE_TARGETS.items():
        if relative == source or source in relative.parents:
            return target / relative.relative_to(source)
    return relative


def init_vault(vault: Path, template: Path = TEMPLATE_DIR, *, force: bool = False) -> InitReport:
    report = InitReport()
    for name in VAULT_REQUIRED_DIRS:
        directory = vault / name
        if not directory.is_dir():
            directory.mkdir(parents=True)
            report.created_dirs.append(name)

    for source in sorted(path for path in template.rglob("*") if path.is_file()):
        relative = _target_for(source.relative_to(template))
        destination = vault / relative
        if destination.exists() and not force:
            report.kept.append(str(relative))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        report.copied.append(str(relative))
    return report


def main(argv: list[str] | None = None) -> InitReport:
    parser = argparse.ArgumentParser(description="Create the JARVIS vault and fill it from vault_template/.")
    parser.add_argument("--vault", type=Path, help="vault directory; defaults to JARVIS_VAULT_DIR")
    parser.add_argument("--force", action="store_true", help="overwrite template files already in the vault")
    args = parser.parse_args(argv)

    settings = Settings()
    configure_logging(settings.model_copy(update={"DEBUG": True, "LOG_LEVEL": "INFO"}))
    vault = (args.vault or settings.JARVIS_VAULT_DIR).expanduser().resolve()

    report = init_vault(vault, force=args.force)
    logger.info(
        "vault_ready",
        vault=str(vault),
        created_dirs=report.created_dirs,
        copied=report.copied,
        kept=report.kept,
    )
    return report


if __name__ == "__main__":
    main()
