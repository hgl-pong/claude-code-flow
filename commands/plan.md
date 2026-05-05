---
name: plan
description: "Plugin plan mode — route planning requests to /workflow-plan instead of Claude Code's built-in plan flow."
---

# Plan

Use the plugin workflow planning pipeline instead of Claude Code's built-in plan mode.

## Process

1. Treat `/plan <task>` as `/workflow-plan <task>`.
2. Use `using-claude-code-flow`, then continue through the workflow-plan gate checklist.
3. Prefer this command for multi-step work, behavior changes, UI work, architecture changes, and cross-file tasks.
4. Use `/quick-fix` only for narrow single-file fixes with a known root cause.
5. Do not invoke built-in plan mode.
6. Do not use `EnterPlanMode`; the workflow-planning pipeline is the intended path.
7. If Claude Code host plan mode is already active, tell the user to exit it and rerun `/plan <task>`.

## Usage

```
/plan Add user authentication with OAuth and JWT
/plan Refactor the database layer
/plan Fix the memory leak
```
