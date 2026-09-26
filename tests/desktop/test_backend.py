import socket
from pathlib import Path

import pytest

from desktop import backend


def test_default_port_is_not_the_usual_dev_port() -> None:
    assert backend.DEFAULT_PORT != 8000


def test_a_listening_socket_counts_as_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        monkeypatch.setattr(backend, "PORT", server.getsockname()[1])

        assert backend.is_port_taken()


def test_another_server_on_the_port_is_not_jarvis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend, "HEALTH_URL", "http://127.0.0.1:9/health")

    assert not backend.is_jarvis_running()


def test_port_taken_by_something_else_is_reported_without_starting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend, "is_jarvis_running", lambda: False)
    monkeypatch.setattr(backend, "is_port_taken", lambda: True)
    started = backend.Backend()

    assert started.ensure_started() is backend.StartResult.PORT_TAKEN
    assert not started.owned


def test_last_error_line_prefers_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    log = tmp_path / "backend.log"
    log.write_text("started\n[error] address already in use\nshutting down\n")
    monkeypatch.setattr(backend, "LOG_FILE", log)

    assert backend.last_error_line() == "[error] address already in use"


def test_last_error_line_without_a_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(backend, "LOG_FILE", tmp_path / "missing.log")

    assert backend.last_error_line() == ""
