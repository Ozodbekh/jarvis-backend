---
paths:
  - "tests/**"
  - "pyproject.toml"
---

# Testing

## The mirror

`tests/` mirrors `app/` one to one: `app/modules/brain/service.py` → `tests/modules/brain/test_service.py`. A new
source file gets its mirror test file in the same change, even if empty, so a missing test is visible. Only
`tests/fakes/` sits outside the mirror.

## Never real

A test never starts a Claude session, never calls the network and never touches the real vault.

- **Claude**: `tests/fakes/claude.py` implements the protocol `app/integrations/claude/` exposes and replays scripted
  messages. The brain service is tested only against it.
- **Vault**: `tests/fakes/vault.py::build_vault` lays one out under `tmp_path`; `JARVIS_VAULT_DIR` points at it.
- **State**: `data/state.json` is redirected into `tmp_path` too.
- **Voice**: `tests/fakes/voice.py` — a transcriber, a speaker and a wake word that fires on loud audio.
  `tests/conftest.py` sets `VOICE_ENABLED=false`, so no model is loaded unless a test passes engines.
- **Desktop**: only `desktop/pcm.py` is unit-tested; the Qt window is checked by rendering it offscreen.

`app/integrations/claude/` itself is covered by a test that builds `ClaudeAgentOptions` from `Settings` and checks
the fields — the one place the SDK's shape is pinned — without connecting.

## Fixtures

`tests/conftest.py`: `settings` (paths under `tmp_path`), `claude` (the fake session), `running_app` (lifespan
run with the fake and a built vault) and `api` (an `httpx` client on it). WebSocket tests build their own
`TestClient`, which runs the lifespan itself.

## Settings

`tests/conftest.py` sets the environment before `app` is imported, because `Settings` is built at import behind an
`lru_cache`. The app under test is built with `create_app()`, never imported as the module-level `app`.

## Markers

A test's kind is a marker, never a folder. `slow` for anything over a second. A `live` marker is reserved for a
manual check against a real Claude session; it is excluded by default and never part of `make check`.

## Async

`asyncio_mode = "auto"`. HTTP through `httpx.AsyncClient` over `ASGITransport`; the WebSocket through FastAPI's
`TestClient`.
