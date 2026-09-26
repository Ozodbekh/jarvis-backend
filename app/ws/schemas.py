from typing import Literal

from pydantic import Field

from app.common.schemas import RequestSchema, ResponseSchema

MAX_COMMAND_LENGTH = 4000


class ClientCommand(RequestSchema):
    type: Literal["command"]
    text: str = Field(min_length=1, max_length=MAX_COMMAND_LENGTH)


class Started(ResponseSchema):
    type: Literal["started"] = "started"


class Delta(ResponseSchema):
    type: Literal["delta"] = "delta"
    text: str


class Tool(ResponseSchema):
    type: Literal["tool"] = "tool"
    name: str


class Done(ResponseSchema):
    type: Literal["done"] = "done"
    text: str
    session_id: str
    cost_usd: float | None
    duration_ms: int


class Error(ResponseSchema):
    type: Literal["error"] = "error"
    code: str
    message: str


type ServerMessage = Started | Delta | Tool | Done | Error


VoiceLanguage = Literal["auto", "uz", "ru", "en"]


class VoiceControl(RequestSchema):
    type: Literal["listen", "played", "language"]
    language: VoiceLanguage | None = None


class VoiceStateMessage(ResponseSchema):
    type: Literal["state"] = "state"
    state: Literal["idle", "listening", "thinking", "speaking"]


class VoiceHeard(ResponseSchema):
    type: Literal["heard"] = "heard"
    text: str
    language: str


class VoiceReply(ResponseSchema):
    type: Literal["reply"] = "reply"
    text: str
