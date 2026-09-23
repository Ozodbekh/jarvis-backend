# JARVIS Backend

A personal voice assistant's backend: FastAPI in front of a Claude Code session driven through the Claude Agent SDK,
with an Obsidian-style markdown vault as its only memory. One user, one machine, localhost only. Decisions and their
reasons are in `docs/STRUCTURE_DECISION.md`. This file holds only what every file obeys.

## Status

Written: `docs/`, the tooling, `app/core/` (config, logging, exceptions), `app/common/schemas.py`, `app/main.py`
with `/health`, and their tests. `app/api/`, `app/ws/`, `app/modules/`, `app/integrations/` are empty packages;
`app/lifespan.py`, `vault_template/` and `scripts/` do not exist yet. Build order: `docs/STRUCTURE_DECISION.md` §9.

## Stack

Python 3.14 · uv · FastAPI 0.141 (`fastapi[standard]`: uvicorn, uvloop, httptools, websockets) ·
`claude-agent-sdk` · Pydantic v2 + pydantic-settings · structlog · pytest + pytest-asyncio + httpx ·
ruff · mypy strict · import-linter. No database, no Redis.

## Layout

| Path | Holds |
|---|---|
| `app/main.py` | `create_app()`, `/health` |
| `app/lifespan.py` | startup/shutdown order: logging → vault check → brain session |
| `app/core/` | config, logging, exceptions — infrastructure, no business rule |
| `app/common/` | shared schema bases and types every module inherits |
| `app/integrations/claude/` | the only package that imports `claude_agent_sdk` |
| `app/integrations/{stt,tts}/` | voice providers, one package each (stage 3) |
| `app/modules/brain/` | the Claude session: one conversation, one command at a time, rotation |
| `app/modules/vault/` | vault paths, layout check, reads for the HUD |
| `app/api/v1/` | HTTP routers and request/response schemas |
| `app/ws/` | the WebSocket endpoint and its message schemas |
| `vault_template/` | JARVIS's own `CLAUDE.md` and `.claude/skills/*/SKILL.md`, copied into the vault |
| `scripts/` | `init_vault.py` and other one-off commands |
| `tests/` | mirrors `app/` one to one: `app/core/config.py` → `tests/core/test_config.py` |
| `docs/` | `STRUCTURE_DECISION.md` and `rules/` — path-scoped rules, indexed by its README |

## Two Claude sessions, never mixed

This file and `docs/rules/` are for the **developer** session working on this repository. JARVIS's **runtime**
session runs with its working directory in the vault and reads `vault_template/`'s copy there. Nothing in
`vault_template/` is an instruction to the developer session, and nothing here reaches JARVIS.

## Commands

`make help` lists everything. `make run` · `lint` · `format` · `typecheck` · `imports` · `test` · `vault`.

`make check` is the definition of done: `ruff check`, `ruff format --check`, `mypy app`, `lint-imports`,
`pytest -q`. Green or not finished.

## Rules

**Boundaries.** Layer order, `core`'s independence and "`claude_agent_sdk` only inside `app/integrations/claude/`"
are contracts in `.importlinter` (`make imports`). Style and the security lint set are ruff's; typing is mypy
strict. Do not restate them in prose.

**Brain.** One `ClaudeSDKClient` per process, one command at a time behind a lock; a second command while one runs
is `BRAIN_BUSY`, never a second session. Options are built in one place from `Settings`. Full form:
`docs/rules/brain.md`.

**Vault.** The vault path comes from `JARVIS_VAULT_DIR`, never a literal. The backend reads the vault; only the
runtime Claude session writes it. `docs/rules/vault.md`.

**HTTP and WebSocket.** Every endpoint declares a `response_model` or a return annotation. Request bodies inherit
`RequestSchema`, responses `ResponseSchema`. The server binds `127.0.0.1` only. `docs/rules/api.md`.

**Errors.** Raise an `AppError` subclass with a machine code — `raise BrainBusyError("BRAIN_BUSY")`. The handler
builds `{code, message, details}`. Never assemble an error response by hand.

**Security.** Secrets are `SecretStr`. The runtime session runs `permission_mode="dontAsk"` with an explicit
`allowed_tools` list; `bypassPermissions` is never used. `docs/rules/brain.md`.

**Logging.** `get_logger()` from `app/core/logging.py`; no `print()`. An event is a snake_case English name plus
keyword fields — `logger.info("command_done", duration_ms=...)`. The user's words and Claude's replies are not
logged at `INFO`.

**Language.** Code, log events and documentation are English. JARVIS answers in the language it was spoken to —
Uzbek, Russian or English — and that is decided in `vault_template/CLAUDE.md`, not in Python. No comments and no
docstrings: `docs/rules/style.md`. Business logic lives in `service.py`, never in a router or WebSocket handler.

**Tests.** A new file gets its mirror test file in the same change. A test never starts a real Claude session or
makes a network call: the brain is tested through a fake client in `tests/fakes/`. `docs/rules/testing.md`.

## Documentation

1. **One scope per file.** This file stays under 150 lines. A `docs/rules/*.md` declares its paths in `paths:`
   frontmatter; `.claude/rules` is a symlink to `docs/rules`.
2. **Never restate a tool.** Name the tool and the command.
3. **Rules here, reasons there.** Why belongs in `docs/STRUCTURE_DECISION.md`; link the section.
4. **Name the guard.** A rule a test enforces cites the test.
5. **Only what is true now**, except `Status` above and `docs/STRUCTURE_DECISION.md` §9, which say what is not
   built yet.
6. **Same change.** Move a file or change a rule and the documentation moves with it.

## Working with the owner

Answers to the owner are in Uzbek, short. One step at a time: finish the step that was agreed, report it, and wait
for the next one. A new dependency, endpoint or directory not in `docs/STRUCTURE_DECISION.md` is asked first.
