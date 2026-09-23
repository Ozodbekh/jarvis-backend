---
paths:
  - "app/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
  - "**/*.md"
---

# Writing code

Formatting, import order, naming form and the security lint set belong to ruff; typing belongs to mypy strict. Both
run in `make check` and are not restated here. This file covers what no tool checks.

## No comments, no docstrings

A comment is the only thing in a source file nothing verifies. When the code around it changes, it stays and
becomes a confident lie. A name, a type, a constant and a test either change with the code or stop the build.

Instead:

- **Name it.** `BRAIN_BUSY`, `MAX_TURNS_BEFORE_ROTATION`, `VAULT_REQUIRED_DIRS` each carry the sentence a comment
  would have.
- **Lift the number out.** A bare `100` says nothing; `DEFAULT_MAX_TURNS = 100` does.
- **Extract the condition.** A branch that needs a comment needs a function name: `_should_rotate()`.
- **Put the why in a document.** A decision belongs in `docs/STRUCTURE_DECISION.md` or a rule file.
- **Write the test.** `test_second_command_while_busy_is_rejected` fails when it stops being true.

Machine directives stay, always with their code: `# noqa: S105`, `# type: ignore[override]`. Never bare.

## Names

- Modules and functions say what they do: `service.py` holds `BrainService.run_command`, not `handle`.
- Error codes are `UPPER_SNAKE`, one per failure: `BRAIN_BUSY`, `BRAIN_FAILED`, `VAULT_MISSING`.
- Log events are `snake_case` past-tense facts: `command_started`, `session_rotated`.

## Language

Code, identifiers, log events, error codes and documents are English. Uzbek, Russian and English text meant for
the user is written by JARVIS at runtime, guided by `vault_template/CLAUDE.md` — Python holds no user-facing
sentences except error messages keyed by code in `app/core/exceptions.py`.

## Async

Everything on the request path is `async`. A blocking call — file reads of unknown size, CPU-heavy work — goes
through `anyio.to_thread.run_sync`, because it would stall the one event loop that also streams the voice.
