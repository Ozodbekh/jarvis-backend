import asyncio

import httpx

from tests.fakes.claude import FakeClaudeSession, reply, result


async def test_command_returns_the_whole_answer(api: httpx.AsyncClient, claude: FakeClaudeSession) -> None:
    claude.replies.append(reply("Bugun uchta vazifa bor.", session_id="s7", num_turns=2))

    response = await api.post("/api/v1/command", json={"text": "  bugungi reja  "})

    assert response.status_code == 200
    assert response.json() == {
        "text": "Bugun uchta vazifa bor.",
        "session_id": "s7",
        "num_turns": 2,
        "duration_ms": 10,
        "cost_usd": 0.001,
    }
    assert claude.prompts == ["bugungi reja"]


async def test_empty_command_is_invalid(api: httpx.AsyncClient) -> None:
    response = await api.post("/api/v1/command", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_unknown_field_is_invalid(api: httpx.AsyncClient) -> None:
    response = await api.post("/api/v1/command", json={"text": "hi", "voice": True})

    assert response.status_code == 422


async def test_busy_brain_answers_conflict(api: httpx.AsyncClient, claude: FakeClaudeSession) -> None:
    claude.gate = asyncio.Event()
    first = asyncio.create_task(api.post("/api/v1/command", json={"text": "slow"}))
    await claude.asked.wait()

    second = await api.post("/api/v1/command", json={"text": "fast"})
    claude.gate.set()

    assert second.status_code == 409
    assert second.json()["code"] == "BRAIN_BUSY"
    assert (await first).status_code == 200


async def test_failed_command_answers_bad_gateway(api: httpx.AsyncClient, claude: FakeClaudeSession) -> None:
    claude.replies.append([result("", is_error=True)])

    response = await api.post("/api/v1/command", json={"text": "hi"})

    assert response.status_code == 502
    assert response.json()["code"] == "BRAIN_FAILED"


async def test_lost_session_answers_unavailable(api: httpx.AsyncClient, claude: FakeClaudeSession) -> None:
    claude.fail_next_ask = True

    response = await api.post("/api/v1/command", json={"text": "hi"})

    assert response.status_code == 503
    assert response.json()["code"] == "BRAIN_UNAVAILABLE"
