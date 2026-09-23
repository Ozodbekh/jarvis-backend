import json
import logging
from collections.abc import Iterator

import pytest

from app.core.config import Settings
from app.core.logging import configure_logging, get_logger


@pytest.fixture(autouse=True)
def _restore_root_logger() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers, root.level = handlers, level


def _last_line(err: str) -> dict[str, object]:
    line: dict[str, object] = json.loads(err.strip().splitlines()[-1])
    return line


def test_production_logs_are_one_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(_env_file=None, DEBUG=False, LOG_LEVEL="INFO"))

    get_logger("app.test").info("command_done", duration_ms=12)

    line = _last_line(capsys.readouterr().err)
    assert line["event"] == "command_done"
    assert line["duration_ms"] == 12
    assert line["level"] == "info"
    assert line["logger"] == "app.test"


def test_uvicorn_logs_share_the_format(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(_env_file=None, DEBUG=False, LOG_LEVEL="INFO"))

    logging.getLogger("uvicorn.error").info("server started")

    line = _last_line(capsys.readouterr().err)
    assert line["event"] == "server started"
    assert line["logger"] == "uvicorn.error"


def test_level_below_the_threshold_is_dropped(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(_env_file=None, DEBUG=False, LOG_LEVEL="WARNING"))

    get_logger("app.test").info("not_shown")

    assert "not_shown" not in capsys.readouterr().err
