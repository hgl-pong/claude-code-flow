---
name: auto-mode
description: Fully automatic development pipeline — brainstorming to merge, no user interaction. Trigger with /auto or 全自动模式
---

# Auto Mode

## Overview

Run the full Claude Code Flow pipeline — brainstorming → writing-plans → subagent-driven-development → finishing — without user interaction. Completion gates run between subagent-driven-development and finishing (tracked as a separate state-machine phase for recovery).

**Core principle:** Automate every decision. Log everything. Never stop unless truly stuck.

**Announce at start:** "I'm using the auto-mode skill to run the full development pipeline autonomously. All decisions will be logged to `.claude/auto/<task-name>/`. Ctrl+C to interrupt at any time."

## Trigger Mechanism

1. `/auto <task description>` — start a new auto-mode pipeline
2. `全自动模式 <task description>` — natural language equivalent
3. `CCF_AUTO_MODE=1` in environment — session-persistent; any task triggers auto-mode, and on session start auto-resumes the most recent dangling task if `.claude/auto/*/state.json` files exist
4. `/auto --resume [task-name]` — resume most recent dangling task, or a specific one by name
5. `/auto --new <task>` — start fresh even if old state.json exists (old audit trail preserved)
6. `/auto --list` — list all dangling auto-mode tasks with status, updated_at, task_name

**Conflict detection:** If your human partner says `/auto <new-task>` while `.claude/auto/*/state.json` files exist, print a warning listing the dangling task(s) and ask: resume old, start new anyway, or cancel.

## Decision Audit Trail

Every decision auto-mode makes that would have been a user interaction is logged to `.claude/auto/<task-name>/`. Create the directory at pipeline start. Write `state.json` immediately.

**Full file formats and directory structure:** See `references/audit-trail.md`.

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
| Implementer DONE_WITH_CONCERNS | Read concerns, address if correctness/scope, proceed | Auto-read concerns. If correctness/scope issues: address, log, re-dispatch. If observations only: note and proceed to review. |
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
| Present 4 options | Wait for user choice | **Default: Option 1 — Merge back to base branch.** Log decision to `decisions.md`. Proceed with merge. |

## Completion Gates (Hard Gates Before Finishing)

These gates fire BEFORE entering the finishing phase. If any gate fails, auto-mode fixes and retries. Do NOT proceed to finishing until ALL gates pass.

| # | Gate | Check | Timeout |
|---|------|-------|---------|
| 1 | All plan tasks executed | `progress.tasks_total == progress.tasks_completed` | 10 iterations |
| 2 | All per-task reviews passed | Spec reviewer ✅ + code reviewer ✅ for each task | 5 iterations/issue |
| 3 | Test suite passes | Run project test command, zero failures | 10 iterations |
| 4 | Verification against spec | Read spec line by line, verify each requirement in codebase | 10 iterations |
| 5 | Final code review passed | Dispatch final reviewer on full diff, must return approved | 5 iterations/issue |
| 6 | Git status clean | `git status --porcelain` empty | 10 iterations |

**Gate order:** 1 → 2 → 3 → 4 → 5 → 6 → enter finishing. Each gate must pass before the next begins.

Gates 2 and 5 use reviewer loops (5-iteration limit per issue, tracked in `reviewer_loop_iterations`). Gates 1, 3, 4, 6 track iterations in `gate_states` entries (10-iteration timeout as backstop). If any gate exceeds its limit, auto-mode stops with: which gate is stuck, what was attempted, what the user can do.

## State Machine & Interruption Recovery

Auto-mode writes `state.json` atomically before every state transition. **Full schema, status values, resume actions, and write timing:** See `references/state-machine.md`.

## Stop Conditions (Only These)

Auto-mode ONLY stops and asks your human partner when:

1. **Requirements are genuinely ambiguous.** The task description could mean multiple, fundamentally different things and no reasonable default exists.
2. **Platform/Infrastructure decision.** High switching cost, no obvious default.
3. **All BLOCKED-retry strategies exhausted.** (1) more capable model, (2) smaller task, (3) additional context — all 3 failed.
4. **Reviewer loop iteration limit hit.** 5-iteration fix → re-review limit exceeded for any single reviewer issue.

When auto-mode stops, it presents exactly what it needs — a single focused question. After answer → update state.json → resume.

Everything else is auto-decided: naming, file structure, library choices, UI layout, testing strategy, error handling patterns, reviewer feedback, merge strategy.

## Worktree Lifecycle

1. **Before implementation:** Create or enter worktree via `Skill("claude-code-flow:using-git-worktrees")` unless already in one. Record `worktree_path` in `state.json`.
2. **During finishing (merge back):** After successful merge, clean up the worktree if auto-mode created it.
3. **On interruption:** Worktree persists. On resume, `state.json` tells auto-mode where the worktree is. `cd` into it before continuing.

## Risk Mitigation

- **All commits are normal git commits.** Your human partner can `git revert` or `git reset` if unhappy.
- **Spec and plan documents are written to disk** (`.claude/specs/`, `.claude/plans/`) before implementation starts.
- **Auto-mode announces decisions as it makes them.** Your human partner sees what's happening, can Ctrl+C to interrupt.
- **No force-push, no destructive git operations.** Same safety rules as normal mode.

## Red Flags

**Never:**
- Start implementation on main/master branch (use worktree)
- Skip any completion gate
- Proceed to finishing with any gate failing
- Assume subagent results on resume without checking git log
- Re-run destructive commands on resume without checking if they already succeeded
- Skip phases because "we probably already did that"
- Ask your human partner for input outside the 4 stop conditions
- Modify existing skill files (auto-mode is additive only)
- Skip writing to audit trail
- Ignore the 5-iteration reviewer loop limit
- Ignore the 10-iteration gate timeout

**Always:**
- Write `state.json` BEFORE every state transition
- Log every automated decision to the appropriate audit file
- Announce decisions as they happen
- Check `gate_states` on resume — do not re-check gates already passed
- Try all 3 BLOCKED-retry strategies before stopping
- Default to Option 1 (merge back) in finishing phase

## Integration

**Required workflow skills:**
- **claude-code-flow:brainstorming** — Phase 1: requirements and design
- **claude-code-flow:writing-plans** — Phase 2: implementation plan
- **claude-code-flow:subagent-driven-development** — Phase 3: execute plan tasks
- **claude-code-flow:finishing-a-development-branch** — Final phase: merge and cleanup
- **claude-code-flow:using-git-worktrees** — Worktree creation and management
- **claude-code-flow:requesting-code-review** — Code review template for reviewer subagents

**Subagents use:**
- **claude-code-flow:test-driven-development** — Subagents follow TDD for each task
