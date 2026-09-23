---
paths:
  - "**/CLAUDE.md"
  - "docs/**"
  - "Makefile"
  - "pyproject.toml"
  - ".importlinter"
---

# Workflow

How work on this repository is done with the owner, and which mechanism enforces which rule.

## One step, then stop

The owner agrees each step before it starts. The order is `docs/STRUCTURE_DECISION.md` §9.

1. Do the step that was agreed, and only that.
2. `make check` green.
3. Update every document the step made untrue, in the same change.
4. Report to the owner in Uzbek, a few lines: what changed, the number that proves it (`12 tests pass`), what is
   next. Then wait.

A step that turns out to need something the plan did not name — a dependency, an endpoint, a directory, a new tool
for the runtime session — is a question to the owner first, with the options.

## Definition of done

`make check`: `ruff check`, `ruff format --check`, `mypy app`, `lint-imports`, `pytest -q`. Green or not finished.
A check is never weakened to pass — no deleted or skipped test, no `# noqa` without its code, no relaxed mypy
setting. If a check is wrong, ask.

## What enforces what

| Rule | Enforced by | Command |
|---|---|---|
| layer order, `core` independent, SDK only in `integrations/claude` | `.importlinter` | `make imports` |
| style, imports, security lint set | ruff | `make lint` |
| types | mypy strict | `make typecheck` |
| behaviour | pytest | `make test` |
| no comments, English, one step at a time | review only | — |

## Git

All work is on `main`; no branches until the owner says so. Commits only when the owner asks. The message in
English. Never push.
