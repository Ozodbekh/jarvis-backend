from dataclasses import dataclass

from claude_agent_sdk import AssistantMessage, Message, ResultMessage, StreamEvent, ToolUseBlock


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolUse:
    name: str


@dataclass(frozen=True, slots=True)
class Result:
    text: str
    session_id: str
    is_error: bool
    subtype: str
    num_turns: int
    duration_ms: int
    cost_usd: float | None


BrainEvent = TextDelta | ToolUse | Result


def _text_delta(event: StreamEvent) -> TextDelta | None:
    if event.parent_tool_use_id is not None or event.event.get("type") != "content_block_delta":
        return None
    delta = event.event.get("delta", {})
    if delta.get("type") != "text_delta":
        return None
    return TextDelta(delta.get("text", ""))


def from_sdk_message(message: Message) -> list[BrainEvent]:
    match message:
        case StreamEvent():
            delta = _text_delta(message)
            return [delta] if delta else []
        case AssistantMessage():
            return [ToolUse(block.name) for block in message.content if isinstance(block, ToolUseBlock)]
        case ResultMessage():
            return [
                Result(
                    text=message.result or "",
                    session_id=message.session_id,
                    is_error=message.is_error,
                    subtype=message.subtype,
                    num_turns=message.num_turns,
                    duration_ms=message.duration_ms,
                    cost_usd=message.total_cost_usd,
                )
            ]
        case _:
            return []
