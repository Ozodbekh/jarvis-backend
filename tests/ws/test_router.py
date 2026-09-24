import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.integrations.claude.events import TextDelta, ToolUse
from app.main import create_app
from tests.fakes.claude import FakeClaudeSession, reply, result
from tests.fakes.vault import build_vault


@pytest.fixture
def client(settings: Settings, claude: FakeClaudeSession) -> Iterator[TestClient]:
    build_vault(settings.JARVIS_VAULT_DIR)
    with TestClient(create_app(settings, claude_session=claude)) as test_client:
        yield test_client


def test_command_streams_started_deltas_tools_and_done(client: TestClient, claude: FakeClaudeSession) -> None:
    claude.replies.append([TextDelta("Sa"), ToolUse("Skill"), TextDelta("lom"), result("Salom", session_id="s3")])

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "command", "text": "salom"})
        messages = [ws.receive_json() for _ in range(5)]

    assert [message["type"] for message in messages] == ["started", "delta", "tool", "delta", "done"]
    assert messages[1]["text"] == "Sa"
    assert messages[2]["name"] == "Skill"
    assert messages[4]["text"] == "Salom"
    assert messages[4]["session_id"] == "s3"


def test_conversation_continues_on_one_socket(client: TestClient, claude: FakeClaudeSession) -> None:
    claude.replies += [reply("bir"), reply("ikki")]

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "command", "text": "1"})
        first = [ws.receive_json() for _ in range(3)]
        ws.send_json({"type": "command", "text": "2"})
        second = [ws.receive_json() for _ in range(3)]

    assert first[-1]["text"] == "bir"
    assert second[-1]["text"] == "ikki"


def test_malformed_message_gets_an_error_and_the_socket_stays_open(
    client: TestClient, claude: FakeClaudeSession
) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        error = ws.receive_json()
        ws.send_json({"type": "command", "text": "hi"})
        after = [ws.receive_json() for _ in range(3)]

    assert error == {"type": "error", "code": "VALIDATION_ERROR", "message": "The request is not valid."}
    assert after[-1]["type"] == "done"


def test_failed_command_sends_an_error(client: TestClient, claude: FakeClaudeSession) -> None:
    claude.replies.append([result("", is_error=True)])

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "command", "text": "hi"})
        message = ws.receive_json()

    assert message["type"] == "error"
    assert message["code"] == "BRAIN_FAILED"


def test_second_command_while_busy_gets_busy_and_disconnect_interrupts(
    client: TestClient, claude: FakeClaudeSession
) -> None:
    claude.gate = asyncio.Event()

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "command", "text": "slow"})
        assert ws.receive_json()["type"] == "started"
        assert ws.receive_json()["type"] == "delta"
        ws.send_json({"type": "command", "text": "fast"})
        busy = ws.receive_json()

    assert busy["code"] == "BRAIN_BUSY"
    assert claude.prompts == ["slow"]
    client.portal.call(asyncio.sleep, 0.05)
    assert claude.interrupts == 1
