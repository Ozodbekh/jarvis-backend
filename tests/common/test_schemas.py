import pytest
from pydantic import ValidationError

from app.common.schemas import RequestSchema, ResponseSchema


class Command(RequestSchema):
    text: str


class Reply(ResponseSchema):
    text: str


class Source:
    text = "salom"


def test_request_strips_whitespace() -> None:
    assert Command(text="  plan today  ").text == "plan today"


def test_request_refuses_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Command.model_validate({"text": "hi", "extra": 1})


def test_response_reads_attributes() -> None:
    assert Reply.model_validate(Source()).text == "salom"
