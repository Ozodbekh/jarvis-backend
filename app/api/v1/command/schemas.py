from pydantic import Field

from app.common.schemas import RequestSchema, ResponseSchema

MAX_COMMAND_LENGTH = 4000


class CommandRequest(RequestSchema):
    text: str = Field(min_length=1, max_length=MAX_COMMAND_LENGTH)


class CommandResponse(ResponseSchema):
    text: str
    session_id: str
    num_turns: int
    duration_ms: int
    cost_usd: float | None
