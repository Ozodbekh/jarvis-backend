import pytest
from pydantic import ValidationError

from app.api.v1.command.schemas import MAX_COMMAND_LENGTH, CommandRequest


def test_command_text_is_stripped() -> None:
    assert CommandRequest(text="  salom ").text == "salom"


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_COMMAND_LENGTH + 1)])
def test_command_text_must_be_present_and_bounded(text: str) -> None:
    with pytest.raises(ValidationError):
        CommandRequest(text=text)
