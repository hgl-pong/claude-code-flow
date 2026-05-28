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

**Conflict detection:** If your human partner says `/auto <new-task>` while `.claude/auto/*/state.json` files exist, print a warning listing the dangling task(s) and ask: resume old, start new anyway, or cancel.

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

## Pipeline with Auto Decisions

Auto-mode orchestrates the existing pipeline, invoking each phase's skill via `Skill("skill-name")`. At every user-interaction gate, auto-mode makes the decision instead of asking.

### Phase 1: Brainstorming

Invoke `Skill("claude-code-flow:brainstorming")` with the task description.

| Gate | Normal Mode | Auto Mode |
|------|-------------|-----------|
| Clarifying questions | Ask user one at a time | Infer reasonable defaults from task description + project context. Log each answer to `clarifications.md`. Proceed. |
| Visual companion offer | Ask user | Skip. Proceed text-only. Log decision to `decisions.md`. |
| Propose 2-3 approaches | Present options, wait for choice | Evaluate approaches. Pick the simplest that fits. Decision rule: existing project patterns > community standard > minimal viable approach. Log to `approaches.md`. Proceed with selected approach. |
| Present design sections | Get approval per section | Auto-approve all sections. Log each to `design-approval.md`. Proceed. |
| User reviews spec | Wait for user to read spec | Skip gate. Log decision to `decisions.md`. Proceed to writing-plans. |

**Decision principles for auto-answering clarifying questions:**
- Scope: YAGNI — cut everything not essential to the stated goal
- Tech choices: follow project existing patterns, otherwise community defaults
- Architecture: simplest decomposition that satisfies the goal
- Style: match existing project conventions

**Subagent dispatches still run:**
Researcher, designer, spec reviewer — these are pipeline components, not user gates. Auto-mode dispatches them exactly as brainstorming would. The difference: when review finds issues, auto-fix without user confirmation. When artifacts are saved, user is not prompted to review them.

### Phase 2: Writing Plans

Invoke `Skill("claude-code-flow:writing-plans")` with the completed spec.

| Gate | Normal Mode | Auto Mode |
|------|-------------|-----------|
| Scope check / subsystem split | Ask user | Auto-split if clearly independent subsystems. Otherwise proceed as single plan. Log decision. |
| Technical research ambiguity | Stop and ask | Auto-resolve with best-guess based on research findings. Log to `decisions.md`. |
| Plan reviewer loop | Fix → re-review until approved, then ask user | Same fix → re-review loop. When reviewer approves, proceed without asking user. |

### Phase 3: Subagent-Driven Development

Invoke `Skill("claude-code-flow:subagent-driven-development")` with the plan.

| Situation | Normal Mode | Auto Mode |
|-----------|-------------|-----------|
| Implementer NEEDS_CONTEXT | Ask user | Auto-search codebase, infer context, re-dispatch with additional info. Log to `decisions.md`. |
| Implementer BLOCKED | Escalate to user | Try in order: (1) re-dispatch with more capable model, (2) split task into smaller pieces, (3) provide additional context from codebase search. Log each attempt. Only stop if all 3 fail. |
| Spec reviewer finds issues | Fix → re-review loop | Same loop, auto-continue until approved. Track iterations in `state.json` `reviewer_loop_iterations`. |
| Code reviewer finds issues | Fix → re-review loop | Same loop, auto-continue until approved. Track iterations. |
| Between tasks | Pause for user check-in | Continuous execution. No pauses. |

**Reviewer Loop Limit:** If the fix → re-review cycle for any single reviewer issue exceeds 5 iterations, auto-mode stops and asks the user. This applies to: plan reviewer, spec reviewer (per-task), code quality reviewer (per-task), and final code reviewer. Track iteration count in `state.json` → `reviewer_loop_iterations` keyed by reviewer type and task/issue.

### Phase 4: Finishing

Invoke `Skill("claude-code-flow:finishing-a-development-branch")`.

| Gate | Normal Mode | Auto Mode |
|------|-------------|-----------|
| Present 4 options | Wait for user choice | **Default: Option 1 — Merge back to base branch.** Log decision. Proceed with merge. |
