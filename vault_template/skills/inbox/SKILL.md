---
name: inbox
description: The morning brief. Use when the owner asks for a brief, a summary of what came in, what is new, or says "morning brief", "ertalabki brifing", "что нового".
---

# inbox

1. Find what is new: notes in `raw/` since the last brief in `outputs/` (or the last two days if there is none),
   today's plan if it exists, and deadlines in `wiki/tasks.md` due in the next three days.
2. Write `outputs/YYYY-MM-DD-brief.md` with three short sections: what came in, what is due, today's plan — each
   item linking its source note as `[[...]]`.
3. Say the brief in at most three sentences: the most important new thing, the nearest deadline, and whether today
   has a plan.

Email, calendar and news are not connected yet. If the owner asks for them, say so in one sentence and give the
brief from the vault.
