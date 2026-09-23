from claude_agent_sdk import AssistantMessage, ResultMessage, StreamEvent, SystemMessage, TextBlock, ToolUseBlock

from app.integrations.claude.events import Result, TextDelta, ToolUse, from_sdk_message


def _delta(text: str, parent: str | None = None) -> StreamEvent:
    return StreamEvent(
        uuid="u1",
        session_id="s1",
        event={"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}},
        parent_tool_use_id=parent,
    )


def test_text_delta_becomes_a_text_event() -> None:
    assert from_sdk_message(_delta("Salom")) == [TextDelta("Salom")]


def test_subagent_text_is_not_spoken() -> None:
    assert from_sdk_message(_delta("inner", parent="tool-1")) == []


def test_other_stream_events_are_dropped() -> None:
    start = StreamEvent(uuid="u2", session_id="s1", event={"type": "message_start", "message": {}})
    thinking = StreamEvent(
        uuid="u3",
        session_id="s1",
        event={"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "hmm"}},
    )

    assert from_sdk_message(start) == []
    assert from_sdk_message(thinking) == []


def test_assistant_tool_calls_become_tool_events() -> None:
    message = AssistantMessage(
        content=[
            TextBlock("Let me check."),
            ToolUseBlock(id="t1", name="Skill", input={}),
            ToolUseBlock(id="t2", name="Read", input={"file_path": "wiki/plan.md"}),
        ],
        model="claude",
    )

    assert from_sdk_message(message) == [ToolUse("Skill"), ToolUse("Read")]


def test_result_carries_the_whole_answer() -> None:
    message = ResultMessage(
        subtype="success",
        duration_ms=1200,
        duration_api_ms=900,
        is_error=False,
        num_turns=2,
        session_id="s1",
        total_cost_usd=0.01,
        result="Bugun uchta vazifa bor.",
    )

    assert from_sdk_message(message) == [
        Result(
            text="Bugun uchta vazifa bor.",
            session_id="s1",
            is_error=False,
            subtype="success",
            num_turns=2,
            duration_ms=1200,
            cost_usd=0.01,
        )
    ]


def test_result_without_text_is_empty() -> None:
    message = ResultMessage(
        subtype="error_max_turns", duration_ms=1, duration_api_ms=1, is_error=True, num_turns=1, session_id="s1"
    )

    [result] = from_sdk_message(message)

    assert isinstance(result, Result)
    assert result.text == ""
    assert result.is_error


def test_system_messages_are_ignored() -> None:
    assert from_sdk_message(SystemMessage(subtype="init", data={})) == []
