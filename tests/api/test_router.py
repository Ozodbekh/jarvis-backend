from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def test_command_is_served_under_api_v1(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, DEBUG=True, JARVIS_VAULT_DIR=tmp_path))

    assert list(app.openapi()["paths"]) == ["/api/v1/command"]
