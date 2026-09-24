---
name: plan
description: Write today's top three tasks. Use when the owner asks to plan the day, asks what to do today or next, or says "plan today", "bugungi reja", "план на сегодня".
---

# plan

1. Read `wiki/tasks.md` if it exists, yesterday's plan in `outputs/`, and anything in `raw/` from the last three
   days that looks like a task or a deadline.
2. Choose at most three tasks for today: deadlines first, then what was left unfinished yesterday, then what the
   owner called important.
3. Write `outputs/YYYY-MM-DD-plan.md`:

   ```
   # Plan — YYYY-MM-DD

   1. <task> — <why today>
   2. ...
   3. ...

   Carried over: [[YYYY-MM-DD-plan]]
   ```

   If today's plan already exists, update it instead of writing a second one.
4. Say the three tasks aloud in one or two sentences. If there is nothing to plan from, say so and ask what matters
   today.
