# JARVIS Backend — architecture decisions

Decisions and the reasoning behind them. The rules that follow from them are in `docs/rules/`, the file map is the
Layout table in the root `CLAUDE.md`. Section numbers are stable; they are cited from elsewhere.

---

## 1. What JARVIS is

Four parts, built in this order (the owner's slides, `images/`):

| Stage | Part | Job |
|---|---|---|
| 1 | Brain — Claude Code + skills | understands a command, picks a skill, does the work, answers |
| 2 | Memory — markdown vault | everything JARVIS knows, as linked markdown files; no database |
| 3 | Voice — STT in, TTS out | push-to-talk; hears and speaks Uzbek, Russian and English |
| 4 | Face — the HUD | one dark terminal-style screen: status, command panel, schedule, audio, vault data |

The loop: voice → backend → Claude session → skill → spoken answer.

## 2. Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.14, `uv` | already in place; same as the owner's other backends |
| Framework | FastAPI with `fastapi[standard]` | async, WebSockets built in, OpenAPI for the HUD |
| Brain | `claude-agent-sdk` | Claude Code as a library: built-in file tools, skills, sessions, permissions (§3) |
| Settings | pydantic-settings | typed `.env`, `SecretStr` |
| Logging | structlog over stdlib | uvicorn logs through stdlib; one format for both |
| Quality | ruff, mypy strict, import-linter, pytest | the `mystylex-backend` gate, unchanged |

Rejected: PostgreSQL and Redis — one user, and the vault is the store (§5). Flask — removed, no async WebSockets.

## 3. The brain

### 3.1 Why the Agent SDK

`myhelperbot-aimind` reaches Claude through Claude Code's own cross-session messaging: named sessions started with
`claude --bg -n <name>`, messages by `SendMessage`. That works between Claude sessions only — a FastAPI process
cannot call `SendMessage`. Its `docs/rules/team.md` also records that a home-made bus over `claude -p --resume`
was tried and dropped.

The Agent SDK gives the same things in-process: a persistent conversation (`ClaudeSDKClient`), streamed messages,
and the flags `aimind` relies on, as options:

| `aimind` launch flag | `ClaudeAgentOptions` field |
|---|---|
| `-n <name>` (the address) | `resume=<session_id>`, the id kept in `data/state.json` |
| `--permission-mode dontAsk` | `permission_mode="dontAsk"` |
| `--settings '{"permissions":{"allow":[…]}}'` | `allowed_tools=[…]` |
| `--append-system-prompt-file <role>` | `system_prompt={"type":"preset","preset":"claude_code","append":…}` |
| started in the worker's checkout | `cwd=<vault>` |
| `--model`, `--effort` | `model`, `effort` |
| `cost.py`, restart past 100 messages | `ResultMessage.total_cost_usd`, `num_turns`; rotation §3.4 |

Field names checked against the installed package, `claude-agent-sdk` 0.2.158 with Claude Code 2.1.280.

### 3.2 Where the session runs

`cwd` is the vault, and `setting_sources=["project"]`, so the session loads the vault's `CLAUDE.md` (JARVIS's
persona and language rule) and `.claude/skills/`. `skills` names the enabled skills explicitly. User settings from
`~/.claude` are not loaded, so the developer's own configuration never leaks into JARVIS.

Credentials are Claude Code's own login on this machine; no API key is stored by the backend. The SDK runs the
Claude Code CLI bundled inside the package, not the one on `PATH` — observed at startup on 2026-09-23 — so upgrading
`claude-agent-sdk` is what upgrades JARVIS's Claude Code.

### 3.3 Permissions

`permission_mode="dontAsk"`: a tool call that would prompt is denied and the session carries on — nobody is at the
terminal to answer a prompt. `allowed_tools` starts at `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Skill`. No `Bash`,
`WebFetch` or `WebSearch` until a skill needs one, and then it is added by name. `bypassPermissions` is never used:
the session writes files on the owner's disk on the strength of a spoken sentence.

### 3.4 One conversation, one command at a time

One user, so one `ClaudeSDKClient` per process, opened in `lifespan` and closed on shutdown. Commands are
serialised by an `asyncio.Lock`; a command that arrives while one runs gets `BRAIN_BUSY` rather than queuing
silently — a spoken command that runs a minute late is worse than one that says it is busy.

The session id from each `ResultMessage` is written to `data/state.json`, so a restart resumes the conversation.
Following `aimind`'s cost measurements, the session is rotated — a fresh one started, the old id dropped — past
`BRAIN_MAX_TURNS` turns. Nothing is lost: the memory is the vault, not the conversation.

### 3.5 Streaming

`include_partial_messages=True`, so text reaches the WebSocket as it is generated and TTS can start speaking before
the answer is finished. `POST /api/v1/command` waits for the `ResultMessage` and returns the whole answer.

## 4. Structure

### 4.1 Layers

`api`/`ws` → `modules/<domain>/service` → `integrations` → `core`. Each calls only downward, enforced by
`.importlinter`. `modules/` does not know `api/` exists.

### 4.2 `integrations/` owns the outside world

`claude_agent_sdk` is imported only in `app/integrations/claude/`, which exposes a small protocol the brain service
depends on. The service is then tested against a fake, and a change in the SDK touches one directory. STT and TTS
follow the same shape in stage 3.

### 4.3 `vault_template/`

JARVIS's persona and its skills are versioned here and copied into the vault by `make vault`. The vault itself is
data, lives outside the repository and is never committed from here. The template stores them as `JARVIS.md` and
`skills/` and the copy renames them, because Claude Code loads any `CLAUDE.md` or `.claude/skills/` under this
repository into the developer session — it did on 2026-09-24 before the rename.

## 5. The vault

`JARVIS_VAULT_DIR`, default `~/jarvis-vault`, outside the repository — it holds personal notes, and the repository
may be pushed. Layout, from the slides:

| Path | Holds |
|---|---|
| `raw/` | everything that comes in, unedited |
| `wiki/` | cleaned, linked knowledge |
| `outputs/` | reports and answers JARVIS produced |
| `CLAUDE.md`, `.claude/skills/` | from `vault_template/` |

Plain markdown with `[[links]]`, so Obsidian opens it as a graph. The backend reads it (HUD, stage 4) and checks its
layout at startup; only the Claude session writes it.

## 6. Skills

Five to start, one `SKILL.md` each, from the slides: `metrics` (pulls the numbers), `inbox` (morning brief),
`trends` (what changed), `plan` (today's top three), `vault` (reads and writes memory). Small single-purpose skills
over one large prompt. A skill that needs an external source gets the tool or MCP server for it when it is written,
not before.

## 7. Voice (stage 3)

Three languages, no GPU. `faster-whisper` on CPU handles Russian and English well and Uzbek less well; a good local
Uzbek TTS voice is the weakest point. Decided: STT and TTS sit behind one protocol each in `app/integrations/`, the
provider is a setting, and the choice between local and a cloud provider is made in stage 3 with measurements.

## 8. Security

- Binds `127.0.0.1` only. The API can make a session edit files; it is not exposed to the network.
- `permission_mode="dontAsk"` plus an explicit allow list (§3.3).
- `.env` is gitignored; `.env.example` is committed.
- The user's words and JARVIS's replies are logged at `DEBUG` only.

## 9. Build order — not built yet

Stage 1, each step reported to the owner before the next:

1. Docs and tooling — **done**.
2. `app/core/` (config, logging, exceptions), `app/common/schemas.py`, `create_app()`, `/health`, their tests —
   **done**.
3. `app/integrations/claude/`: the protocol and the SDK-backed client — **done**.
4. `app/modules/brain/`: service, lock, state file, rotation; `app/modules/vault/`: path and layout check;
   `app/lifespan.py` — **done**. The SDK contract in `.importlinter` allows indirect imports: a module reaching the
   SDK through `app.integrations.claude` is the design, a direct `import claude_agent_sdk` is still refused
   (probed 2026-09-23).
5. `POST /api/v1/command` and `WS /ws` — **done**; run end to end against a real session on 2026-09-24: an
   Uzbek command over HTTP and a Russian one over the WebSocket, each answered in its language, one session.
6. `vault_template/` with the persona and the five skills; `scripts/init_vault.py`; `make vault` — **done**.

Stage 1 ran end to end on 2026-09-24 against `~/jarvis-vault`: "remember", a metric, today's plan and a recall, in
Uzbek, each answered in Uzbek and written to the right folder. A command that writes notes took 9–13 s and a plain
recall 3 s — the number stage 3 has to live with.

Proposed to the owner, not yet agreed: voice (stage 3) before the memory work of stage 2, which the vault covers for
now. Stage 3 decides the TTS provider for Uzbek and where the microphone lives (the browser HUD or this machine).

## 10. Still open

- The model and effort JARVIS runs at — a setting; chosen by measuring latency on real commands.
- Whether the HUD is served by this backend or is a separate frontend (stage 4).
- An auth token on the WebSocket if the HUD ever runs on another device.
- Whether `ResultMessage.total_cost_usd` is per command or the connected session's running total: two commands on
  one session reported 0.036 then 0.111. Settle before the HUD shows a cost.
