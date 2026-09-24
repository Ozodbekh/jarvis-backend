import pytest
from fastapi import FastAPI
from starlette.requests import HTTPConnection

from app.modules.brain.exceptions import BrainUnavailableError
from app.ws.deps import get_brain


def test_missing_brain_is_unavailable() -> None:
    connection = HTTPConnection({"type": "websocket", "app": FastAPI(), "headers": []})

    with pytest.raises(BrainUnavailableError):
        get_brain(connection)
