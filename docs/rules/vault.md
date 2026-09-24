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

Versioned here, copied into the vault by `make vault` (`python -m scripts.init_vault`, `--vault` and `--force`).

- `vault_template/JARVIS.md` becomes the vault's `CLAUDE.md`: JARVIS's persona — who it is, that it answers in the
  language it was spoken to (Uzbek, Russian, English), that answers are short enough to be spoken, where each kind
  of note goes, and that it has file tools only.
- `vault_template/skills/<name>/SKILL.md` becomes `.claude/skills/<name>/SKILL.md`, one per skill, with `name` and
  `description` frontmatter. Small and single-purpose; the description says when to use it, in the owner's words in
  all three languages. The set of skills equals `BRAIN_SKILLS`' default.
- The template never holds a file named `CLAUDE.md` or a `.claude/` directory. Observed 2026-09-24: Claude Code
  loaded `vault_template/.claude/skills/` into the developer session as its own skills. The renaming happens in
  `scripts/init_vault.py::TEMPLATE_TARGETS`.
- `init_vault.py` creates missing directories and copies template files that are missing. It never overwrites a
  file that exists unless run with `--force`, because the owner may have edited it in the vault.

The persona and skills are instructions to JARVIS, not to the developer session (root `CLAUDE.md`, "Two Claude
sessions"). Guarded by `tests/scripts/test_init_vault.py`: the mapping, keep-unless-forced, the skill set and each
skill's frontmatter.
