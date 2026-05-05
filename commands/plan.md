---
name: plan
description: "Plugin plan mode — route planning requests to /workflow-plan instead of Claude Code's built-in plan flow."
---

# Plan

Use the plugin workflow planning pipeline.

## Process

1. Use `/workflow-plan` for the full planning flow.
2. Prefer this command for multi-step work, behavior changes, UI work, architecture changes, and cross-file tasks.
3. Use `/quick-fix` only for narrow single-file fixes with a known root cause.

## Usage

```
/plan Add user authentication with OAuth and JWT
/plan Refactor the database layer
/plan Fix the memory leak
```
