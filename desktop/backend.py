import json
import os
import signal
import socket
import subprocess
import sys
import urllib.request
from enum import StrEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT = int(os.environ.get("JARVIS_PORT", DEFAULT_PORT))
HEALTH_URL = f"http://{HOST}:{PORT}/health"
LOG_FILE = ROOT / "data" / "backend.log"
STOP_TIMEOUT_S = 15
LOG_TAIL_BYTES = 4000


class StartResult(StrEnum):
    ALREADY_RUNNING = "already_running"
    STARTED = "started"
    PORT_TAKEN = "port_taken"


def is_jarvis_running() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=1) as response:
            return bool(response.status == 200 and json.loads(response.read()) == {"status": "ok"})
    except OSError, ValueError:
        return False


def is_port_taken() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((HOST, PORT)) == 0


def last_error_line() -> str:
    if not LOG_FILE.is_file():
        return ""
    with LOG_FILE.open("rb") as log:
        log.seek(max(0, LOG_FILE.stat().st_size - LOG_TAIL_BYTES))
        lines = log.read().decode(errors="replace").splitlines()
    errors = [line for line in lines if "error" in line.lower()]
    return (errors or lines or [""])[-1][-200:]


class Backend:
    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def owned(self) -> bool:
        return self._process is not None

    def ensure_started(self) -> StartResult:
        if is_jarvis_running():
            return StartResult.ALREADY_RUNNING
        if is_port_taken():
            return StartResult.PORT_TAKEN
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        log = LOG_FILE.open("ab")
        self._process = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", str(PORT)],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        return StartResult.STARTED

    def exited(self) -> bool:
        return self._process is not None and self._process.poll() is not None

    def stop(self) -> None:
        if self._process is None or self._process.poll() is not None:
            return
        self._process.send_signal(signal.SIGINT)
        try:
            self._process.wait(timeout=STOP_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self._process.kill()
