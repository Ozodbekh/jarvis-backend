---
paths:
  - "app/api/**"
  - "app/ws/**"
  - "app/common/schemas.py"
---

# HTTP and WebSocket

## Routers are thin

A router or WebSocket handler parses input, calls one service method and shapes the output. No business rule, no
`claude_agent_sdk` import (`.importlinter`), no vault path arithmetic.

## Schemas

Request bodies inherit `RequestSchema` (`extra="forbid"`, strings stripped); responses inherit `ResponseSchema`.
Every endpoint declares a `response_model` or a return annotation. Schemas live in the `schemas.py` beside their
router.

## Errors

Raise an `AppError` subclass with a machine code. The handler in `app/core/exceptions.py` answers
`{code, message, details}` with the subclass's status. Never build an error response by hand.

| Code | Status | When |
|---|---|---|
| `BRAIN_BUSY` | 409 | a command arrives while another runs |
| `BRAIN_FAILED` | 502 | the session ended in an error |
| `BRAIN_UNAVAILABLE` | 503 | the session is not connected |
| `VAULT_MISSING` | 503 | the vault directory or its layout is missing |

## Endpoints

| Method and path | Does |
|---|---|
| `GET /health` | answers from memory; hidden from the schema |
| `POST /api/v1/command` | `{text}` → the whole answer, the session id, cost and duration |
| `WS /ws` | the streamed conversation, below |
| `WS /ws/voice` | binary 16 kHz int16 audio in; `state`, `heard`, `reply`, `error` JSON and one WAV per reply out — `docs/rules/voice.md` |

## The WebSocket message shape

JSON objects with a `type`. The client sends `{"type": "command", "text": "..."}`. The server sends, in order:

| `type` | Carries |
|---|---|
| `started` | nothing — sent with the first event, so a busy command gets `error` and never `started` |
| `delta` | `text`: the next piece of the answer |
| `tool` | `name`: a tool or skill the session is using, for the HUD |
| `done` | `text` (the whole answer), `session_id`, `cost_usd`, `duration_ms` |
| `error` | `code`, `message` |

One command at a time per process, WebSocket or HTTP alike; the second gets `error` with `BRAIN_BUSY`. The shape is
defined once as Pydantic models in `app/ws/schemas.py` and the HUD is built against it.

Each command on a socket runs in its own task while the handler keeps reading, so a second command is answered
`BRAIN_BUSY` at once and a disconnect cancels the running command, which interrupts the session
(`tests/ws/test_router.py::test_second_command_while_busy_gets_busy_and_disconnect_interrupts`). A malformed message
gets `VALIDATION_ERROR` and the socket stays open.

## Getting the brain

`app/api/deps.py` and `app/ws/deps.py` hold the same six-line `get_brain`: `.importlinter` keeps `app.api` and
`app.ws` independent, and the getter reads `app.state`, which only this layer may know about.

## Binding

`127.0.0.1` only (`docs/STRUCTURE_DECISION.md` §8). `make run` passes `--host 127.0.0.1`.
