---
paths:
  - "app/modules/vault/**"
  - "vault_template/**"
  - "scripts/init_vault.py"
---

# The vault

The reasons are `docs/STRUCTURE_DECISION.md` §5 and §6.

## Path and layout

`JARVIS_VAULT_DIR`, expanded and resolved once in `Settings`. Required: `raw/`, `wiki/`, `outputs/`, `CLAUDE.md`,
`.claude/skills/`. `lifespan` checks the layout and refuses to start with `VAULT_MISSING` naming what is absent —
a brain with no memory would answer confidently from nothing.

## Who writes

Only the runtime Claude session writes the vault. The backend reads it — for the HUD and the layout check — and
never edits a note. A read resolves the path and refuses anything outside the vault root.

## `vault_template/`

Versioned here, copied into the vault by `make vault` (`scripts/init_vault.py`).

- `vault_template/CLAUDE.md` is JARVIS's persona: who it is, that it answers in the language it was spoken to
  (Uzbek, Russian, English), that answers are short enough to be spoken, where each kind of note goes.
- `vault_template/.claude/skills/<name>/SKILL.md`, one per skill, with `name` and `description` frontmatter.
  Small and single-purpose; the description says when to use it.
- `init_vault.py` creates missing directories and copies template files that are missing. It never overwrites a
  file that exists unless run with `--force`, because the owner may have edited it in the vault.

The persona and skills are instructions to JARVIS, not to the developer session (root `CLAUDE.md`, "Two Claude
sessions").
