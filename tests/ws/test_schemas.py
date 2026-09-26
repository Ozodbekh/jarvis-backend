import json

import pytest
from pydantic import ValidationError

from app.ws.schemas import ClientCommand, Delta, Done, Error, Started, Tool


def test_client_command_is_parsed_and_stripped() -> None:
    command = ClientCommand.model_validate_json('{"type": "command", "text": "  salom  "}')

    assert command.text == "salom"


@pytest.mark.parametrize(
    "raw",
    [
        '{"type": "command", "text": ""}',
        '{"type": "stop"}',
        '{"text": "hi"}',
        '{"type": "command", "text": "a", "x": 1}',
    ],
)
def test_malformed_client_messages_are_refused(raw: str) -> None:
    with pytest.raises(ValidationError):
        ClientCommand.model_validate_json(raw)


def test_server_messages_carry_their_type() -> None:
    assert json.loads(Started().model_dump_json()) == {"type": "started"}
    assert json.loads(Delta(text="Sa").model_dump_json()) == {"type": "delta", "text": "Sa"}
    assert json.loads(Tool(name="Skill").model_dump_json()) == {"type": "tool", "name": "Skill"}
    assert json.loads(Error(code="BRAIN_BUSY", message="m").model_dump_json())["type"] == "error"
    done = Done(text="ok", session_id="s1", cost_usd=None, duration_ms=5)
    assert json.loads(done.model_dump_json())["type"] == "done"


def test_voice_control_accepts_only_known_types() -> None:
    from app.ws.schemas import VoiceControl

    assert VoiceControl.model_validate_json('{"type": "listen"}').type == "listen"
    assert VoiceControl.model_validate_json('{"type": "played"}').type == "played"
    with pytest.raises(ValidationError):
        VoiceControl.model_validate_json('{"type": "dance"}')


def test_language_control_takes_a_known_language() -> None:
    from app.ws.schemas import VoiceControl

    assert VoiceControl.model_validate_json('{"type": "language", "language": "uz"}').language == "uz"
    with pytest.raises(ValidationError):
        VoiceControl.model_validate_json('{"type": "language", "language": "fr"}')
