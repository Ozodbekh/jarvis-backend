---
paths:
  - "app/integrations/claude/**"
  - "app/modules/brain/**"
  - "app/lifespan.py"
---

# The brain

The reasons are `docs/STRUCTURE_DECISION.md` §3. This file is how the code must look.

## The boundary

`app/integrations/claude/` is the only package that imports `claude_agent_sdk` (`.importlinter`). It exposes:

- a `Protocol` the brain depends on — connect, send a prompt, iterate the resulting events, interrupt, disconnect;
- the SDK-backed implementation of it;
- `build_options(settings, session_id)` — the one place `ClaudeAgentOptions` is built.

The events crossing the boundary are this package's own small dataclasses (text delta, tool use, result), not SDK
types, so `modules/` never sees the SDK.

## Options

Built from `Settings`, never from literals in a service:

| Field | Value |
|---|---|
| `cwd` | the vault, `JARVIS_VAULT_DIR` |
| `setting_sources` | `["project"]` — the vault's `CLAUDE.md` and skills, not the developer's `~/.claude` |
| `skills` | the enabled skill names, `BRAIN_SKILLS` |
| `permission_mode` | `"dontAsk"` |
| `allowed_tools` | `BRAIN_ALLOWED_TOOLS`, default `Read, Write, Edit, Glob, Grep, Skill` |
| `system_prompt` | the `claude_code` preset with a short `append` naming JARVIS and the backend's constraints |
| `model`, `effort` | `BRAIN_MODEL`, `BRAIN_EFFORT`; unset means Claude Code's default |
| `resume` | the stored session id, or none for a fresh session |
| `include_partial_messages` | `True` |

`bypassPermissions` is never used. A tool is added to the allow list by name, when a skill needs it, with the
owner's word — never `Bash` wholesale.

## The service

- One client per process, connected in `lifespan`, disconnected on shutdown.
- `asyncio.Lock`; `lock.locked()` at entry raises `BrainBusyError("BRAIN_BUSY")` instead of waiting.
- Each result's `session_id` is written to the state file; `num_turns` summed across results decides rotation past
  `BRAIN_MAX_TURNS`.
- A `ResultMessage` with `is_error` raises `BrainFailedError("BRAIN_FAILED")` with its `subtype` in `details`.
- A WebSocket that disconnects mid-command interrupts the session, so a dropped client does not leave work running.

## Logging

`command_started`, `command_done` (duration, cost, turns), `session_rotated`, `command_failed`. The prompt and the
answer only at `DEBUG`.
