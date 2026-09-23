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

## The WebSocket message shape

JSON objects with a `type`. The client sends `{"type": "command", "text": "..."}`. The server sends, in order:

| `type` | Carries |
|---|---|
| `started` | nothing — the command was accepted |
| `delta` | `text`: the next piece of the answer |
| `tool` | `name`: a tool or skill the session is using, for the HUD |
| `done` | `text` (the whole answer), `session_id`, `cost_usd`, `duration_ms` |
| `error` | `code`, `message` |

One command at a time per process, WebSocket or HTTP alike; the second gets `error` with `BRAIN_BUSY`. The shape is
defined once as Pydantic models in `app/ws/schemas.py` and the HUD is built against it.

## Binding

`127.0.0.1` only (`docs/STRUCTURE_DECISION.md` §8). `make run` passes `--host 127.0.0.1`.
