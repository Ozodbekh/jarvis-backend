import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.integrations.stt.whisper import Transcript
from app.main import create_app
from tests.fakes.claude import FakeClaudeSession, reply
from tests.fakes.vault import build_vault
from tests.fakes.voice import LOUD, FakeTranscriber, audio, fake_engines


@pytest.fixture
def transcriber() -> FakeTranscriber:
    return FakeTranscriber()


@pytest.fixture
def client(settings: Settings, claude: FakeClaudeSession) -> Iterator[tuple[TestClient, FakeTranscriber]]:
    build_vault(settings.JARVIS_VAULT_DIR)
    engines, transcriber, _, _ = fake_engines()
    app = create_app(
        settings.model_copy(update={"VOICE_SILENCE_MS": 400}), claude_session=claude, voice_engines=engines
    )
    with TestClient(app) as test_client:
        yield test_client, transcriber


def test_voice_socket_speaks_back(client: tuple[TestClient, FakeTranscriber], claude: FakeClaudeSession) -> None:
    test_client, transcriber = client
    transcriber.transcripts.append(Transcript("Rejam nima?", "uz"))
    claude.replies.append(reply("Bugun bitta uchrashuv bor."))

    with test_client.websocket_connect("/ws/voice") as ws:
        assert ws.receive_json() == {"type": "state", "state": "idle"}
        ws.send_bytes(audio(0.08, LOUD))
        ws.send_bytes(audio(0.48, LOUD))
        ws.send_bytes(audio(0.56))
        messages = []
        while True:
            message = ws.receive()
            if message.get("bytes"):
                messages.append("<wav>")
                break
            messages.append(json.loads(message["text"]))
        ws.send_json({"type": "played"})
        assert ws.receive_json() == {"type": "state", "state": "idle"}

    assert messages[0] == {"type": "state", "state": "listening"}
    assert messages[1] == {"type": "state", "state": "thinking"}
    assert {"type": "heard", "text": "Rejam nima?", "language": "uz"} in messages
    assert {"type": "reply", "text": "Bugun bitta uchrashuv bor."} in messages
    assert messages[-2:] == [{"type": "state", "state": "speaking"}, "<wav>"]


def test_push_to_talk_over_the_socket(client: tuple[TestClient, FakeTranscriber]) -> None:
    test_client, _ = client

    with test_client.websocket_connect("/ws/voice") as ws:
        ws.receive_json()
        ws.send_json({"type": "listen"})

        assert ws.receive_json() == {"type": "state", "state": "listening"}


def test_bad_control_message_gets_an_error(client: tuple[TestClient, FakeTranscriber]) -> None:
    test_client, _ = client

    with test_client.websocket_connect("/ws/voice") as ws:
        ws.receive_json()
        ws.send_text('{"type": "dance"}')

        assert ws.receive_json()["code"] == "VALIDATION_ERROR"


def test_voice_socket_is_refused_when_voice_is_off(settings: Settings, claude: FakeClaudeSession) -> None:
    build_vault(settings.JARVIS_VAULT_DIR)
    with (
        TestClient(create_app(settings, claude_session=claude)) as test_client,
        pytest.raises(WebSocketDisconnect),
        test_client.websocket_connect("/ws/voice") as ws,
    ):
        ws.receive_json()


def test_language_control_reaches_the_transcriber(
    client: tuple[TestClient, FakeTranscriber], claude: FakeClaudeSession
) -> None:
    test_client, transcriber = client

    with test_client.websocket_connect("/ws/voice") as ws:
        ws.receive_json()
        ws.send_json({"type": "language", "language": "ru"})
        ws.send_json({"type": "listen"})
        ws.receive_json()
        ws.send_bytes(audio(0.48, LOUD))
        ws.send_bytes(audio(0.56))
        while ws.receive_json() != {"type": "state", "state": "thinking"}:
            pass

    assert transcriber.languages[-1] == "ru"
