---
paths:
  - "docs/rules/**"
---

# Rules

Rules that apply to part of the tree. The root `CLAUDE.md` holds what every file obeys; anything narrower lives here
so a session loads it only when it works on that part. `.claude/rules` is a symlink to this directory, so the files
are reviewed like any other document.

## How a rule file is selected

Every file opens with a `paths:` frontmatter block. Claude Code loads the file when a matching path is read.

## Files

| File | Loads on | Covers |
|---|---|---|
| `style.md` | every `.py` and `.md` | no comments and what to write instead, names, English |
| `workflow.md` | `**/CLAUDE.md`, `docs/**`, `Makefile`, `pyproject.toml`, `.importlinter` | the step-by-step loop with the owner, the definition of done, which tool enforces what |
| `testing.md` | `tests/**`, `pyproject.toml` | the mirror tree, fakes, markers, what a test may never do |
| `api.md` | `app/api/**`, `app/ws/**`, `app/common/schemas.py` | routers, schemas, errors, the WebSocket message shape |
| `brain.md` | `app/integrations/claude/**`, `app/modules/brain/**`, `app/lifespan.py` | the session, options, permissions, the lock, rotation, streaming |
| `vault.md` | `app/modules/vault/**`, `vault_template/**`, `scripts/init_vault.py` | the vault path and layout, who writes it, skills and the persona |

## What belongs in a rule file

- A rule states its reason, or links the section of `docs/STRUCTURE_DECISION.md` that does.
- Never restate ruff, mypy or `.importlinter`; name the command.
- A rule a test enforces cites the test file.
- Under 200 lines.

## Conflicts

Root `CLAUDE.md` > a rule file > habit. If a rule is wrong, change the rule in the same change as the code.
