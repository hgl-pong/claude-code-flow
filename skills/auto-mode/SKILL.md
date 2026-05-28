---
name: auto-mode
description: Fully automatic development pipeline — brainstorming to merge, no user interaction. Trigger with /auto or 全自动模式
---

# Auto Mode

## Overview

Run the full Claude Code Flow pipeline — brainstorming → writing-plans → subagent-driven-development → finishing — without user interaction. At every gate where normal mode would ask the user, auto-mode makes the decision, logs it, and continues. Only stops when genuinely blocked by irreplaceable missing information.

**Core principle:** Automate every decision. Log everything. Never stop unless truly stuck.

**Announce at start:** "I'm using the auto-mode skill to run the full development pipeline autonomously. All decisions will be logged to `.claude/auto/<task-name>/`. Ctrl+C to interrupt at any time."

## Trigger Mechanism

Auto-mode activates via:

1. `/auto <task description>` — start a new auto-mode pipeline
2. `全自动模式 <task description>` — natural language equivalent
3. `CCF_AUTO_MODE=1` in environment — session-persistent; any task triggers auto-mode, and on session start auto-resumes the most recent dangling task if `.claude/auto/*/state.json` files exist
4. `/auto --resume [task-name]` — resume most recent dangling task, or a specific one by name
5. `/auto --new <task>` — start fresh even if old state.json exists (old audit trail preserved)
6. `/auto --list` — list all dangling auto-mode tasks with status, updated_at, task_name

**Conflict detection:** If user says `/auto <new-task>` while `.claude/auto/*/state.json` files exist, print a warning listing the dangling task(s) and ask: resume old, start new anyway, or cancel.

**Multiple dangling tasks on auto-resume:** Glob `.claude/auto/*/state.json`, sort by `updated_at`, pick most recent. Print: "Resuming auto-mode task `<name>` from `<timestamp>`. Use `/auto --new <task>` to start fresh, `/auto --resume <task-name>` to resume a different one, or `/auto --list` to see all."

## Decision Audit Trail

Every decision auto-mode makes that would have been a user interaction is logged to `.claude/auto/<task-name>/`.

### Directory Structure

```
.claude/auto/<task-name>/
├── state.json           # Current pipeline state — used for interruption recovery
├── decisions.md         # Decision log — one entry per automated choice
├── clarifications.md    # Auto-answered clarifying questions + reasoning
├── approaches.md        # Approach comparison + which was picked + why
├── design-approval.md   # Design sections and auto-approval record
└── plan-checklist.md    # Gate results (all 6 gates) with pass/fail timestamps
```

### File Creation Order

Create `.claude/auto/<task-name>/` directory at pipeline start. Write `state.json` immediately (initial state). Other files are written as the pipeline progresses:

- `clarifications.md` — during brainstorming phase, one entry per inferred answer
- `approaches.md` — after research, before design
- `design-approval.md` — section by section as design is auto-approved
- `decisions.md` — append-only, throughout all phases
- `plan-checklist.md` — during completion gate phase, updated as each gate passes

### `decisions.md` Format

Every entry follows this exact format:

```markdown
## [timestamp] [phase] <decision summary>

**What would have been asked:** <the user gate being bypassed>
**Decision:** <what auto-mode chose>
**Reasoning:** <why — project pattern / community default / YAGNI / etc.>
**Alternatives considered:** <what else was considered, why rejected>
```

### `clarifications.md` Format

```markdown
# Auto-Answered Clarifying Questions

## Clarifying Question 1

**Question auto-mode inferred:** <what was unclear>
**Auto-answer:** <what was assumed>
**Basis:** <project context / file evidence / reasonable default>
**Risk:** LOW | MEDIUM | HIGH — <what could go wrong if this is wrong>
```

### `approaches.md` Format

```markdown
# Approach Selection

## Approach A: <name> (REJECTED)
- **Description:** ...
- **Why rejected:** ...

## Approach B: <name> (SELECTED)
- **Description:** ...
- **Why selected:** ...

## Approach C: <name> (REJECTED)
- **Description:** ...
- **Why rejected:** ...
```

### `design-approval.md` Format

```markdown
# Design Section Auto-Approvals

## Section: <name>
**Status:** APPROVED
**Content:** <summary of what was approved>
**Timestamp:** <ISO timestamp>
```

### Pipeline End Summary

When auto-mode finishes (including successful merge), print:

```
Auto-mode complete. Decision trail at .claude/auto/<task-name>/
  - N clarifying questions auto-answered
  - M approaches evaluated
  - 6/6 completion gates passed
  - 0 user interruptions needed

Review: cat .claude/auto/<task-name>/decisions.md
Revert: git revert <merge-commit>
```
