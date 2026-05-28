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

Auto-mode activates via:

1. `/auto <task description>` — start a new auto-mode pipeline
2. `全自动模式 <task description>` — natural language equivalent
3. `CCF_AUTO_MODE=1` in environment — session-persistent; any task triggers auto-mode, and on session start auto-resumes the most recent dangling task if `.claude/auto/*/state.json` files exist
4. `/auto --resume [task-name]` — resume most recent dangling task, or a specific one by name
5. `/auto --new <task>` — start fresh even if old state.json exists (old audit trail preserved)
6. `/auto --list` — list all dangling auto-mode tasks with status, updated_at, task_name

**Conflict detection:** If your human partner says `/auto <new-task>` while `.claude/auto/*/state.json` files exist, print a warning listing the dangling task(s) and ask: resume old, start new anyway, or cancel.

**Multiple dangling tasks on auto-resume:** See Resume Flow in the State Machine section below for how multiple dangling state.json files are resolved.

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

**Subagent dispatches still run:**
Technical researcher — dispatched by the writing-plans skill for codebase + web research. Auto-mode lets it run normally. When research reveals ambiguity, auto-resolve with best-guess rather than stopping.

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

## State Machine & Interruption Recovery

Auto-mode writes `state.json` atomically before every state transition. This is the single source of truth for resuming after session interruption.

### `state.json` Schema

```json
{
  "task_name": "<sanitized task name slug>",
  "phase": "<brainstorming|writing-plans|subagent-driven-development|completion-gates|finishing>",
  "status": "<DECIDING|AWAITING_SUBAGENT|AWAITING_SHELL|EXECUTING_GATE|STOPPED_ASK_USER|FINISHING|DONE>",
  "status_detail": {
    "agent_id": "<subagent id, if AWAITING_SUBAGENT>",
    "agent_name": "<implementer-task-N>",
    "task_id": "<plan task id>",
    "dispatched_at": "<ISO timestamp>",
    "redispatched": false
  },
  "progress": {
    "phase_order": ["brainstorming", "writing-plans", "subagent-driven-development", "completion-gates", "finishing"],
    "completed": [],
    "current": "brainstorming",
    "pending": ["writing-plans", "subagent-driven-development", "completion-gates", "finishing"],
    "tasks_total": 0,
    "tasks_completed": 0,
    "tasks_reviewed": 0
  },
  "spec_path": ".claude/specs/<spec-file>",
  "plan_path": ".claude/plans/<plan-file>",
  "decision_trail": ".claude/auto/<task-name>/decisions.md",
  "worktree_path": "<path, if applicable>",
  "stopped_question": null,
  "last_command": null,
  "current_step": "<legal current_step value>",
  "gate_states": {
    "gate_1_tasks_executed": { "passed": false, "iterations": 0 },
    "gate_2_reviews_passed": { "passed": false, "iterations": 0 },
    "gate_3_tests_pass": { "passed": false, "iterations": 0 },
    "gate_4_spec_verified": { "passed": false, "iterations": 0 },
    "gate_5_final_review": { "passed": false, "iterations": 0 },
    "gate_6_git_clean": { "passed": false, "iterations": 0 }
  },
  "reviewer_loop_iterations": {},
  "updated_at": "<ISO timestamp>"
}
```

### `current_step` Legal Values

| Phase | `current_step` value |
|---|---|
| brainstorming | `explore-context` |
| brainstorming | `offer-visual-companion` |
| brainstorming | `clarifying-questions` |
| brainstorming | `dispatch-researcher` |
| brainstorming | `dispatch-designer` |
| brainstorming | `propose-approaches` |
| brainstorming | `present-design` |
| brainstorming | `write-spec` |
| brainstorming | `spec-review-loop` |
| writing-plans | `scope-check` |
| writing-plans | `technical-research` |
| writing-plans | `write-plan` |
| writing-plans | `plan-review-loop` |
| subagent-driven-development | `dispatch-implementer` |
| subagent-driven-development | `spec-review-loop` |
| subagent-driven-development | `code-review-loop` |
| completion-gates | `running-gates` |
| finishing | `merging` |

### Status Values and Resume Actions

| `status` | Meaning | Resume Action |
|---|---|---|
| `DECIDING` | In a decision loop (clarifying, approaches, design) | Read `current_step`, `clarifications.md`, and `decisions.md`. Skip decisions already logged. Resume from the step indicated by `current_step`. |
| `AWAITING_SUBAGENT` | Dispatched subagent, waiting for reply | (1) Run `git log --oneline -3` — if the task's expected commit message appears, the subagent finished before session ended; read code and proceed to review. (2) If no commit found, re-dispatch with same prompt and mark `redispatched: true` in state. |
| `AWAITING_SHELL` | Running a shell command | Read `last_command` from state.json. If idempotent (test, lint, build, search) → re-run. If state-mutating (commit, merge, push, rm, install) → check whether intended state already exists (e.g., `git log --oneline -1` for commit). If already done → skip and proceed. If not done → re-run. |
| `EXECUTING_GATE` | Running completion gate checks | Read `gate_states` from state.json. Resume from the first gate where `passed` is `false`. Do NOT re-check gates already `true` — they were verified on disk. |
| `STOPPED_ASK_USER` | Auto-mode stopped to ask user a question | Do NOT auto-resume. Print the stored question (`stopped_question` in state.json) and wait. When user answers, update status to resume from where it stopped. |
| `FINISHING` | In finishing phase (merge) | Re-check git state, continue merge. |
| `DONE` | Pipeline complete | Nothing to do. Print summary. |

### Write Timing for `state.json`

Update `state.json` BEFORE every state transition. Key moments:
- After creating audit directory → write initial state
- Before dispatching subagent → set `AWAITING_SUBAGENT`
- Before running shell command → set `AWAITING_SHELL` + `last_command`
- Before entering a decision → set `DECIDING` + `current_step`
- Between pipeline phases → update `phase`, `progress`
- When stopped to ask user → set `STOPPED_ASK_USER` + `stopped_question`
- After each completion gate → update `gate_states`

### Resume Flow

When resuming (`/auto --resume` or `CCF_AUTO_MODE=1` on startup):

1. Read `.claude/auto/<task-name>/state.json`
2. Read `status`
3. Switch on status (see status table above for per-status actions)
4. Set `phase` to the current pipeline phase from `state.json`. Set `current_step` to the first step of that phase (see `current_step` Legal Values table for the first step per phase)
5. Update `state.json` BEFORE every subsequent state change

If `.claude/auto/*/state.json` files exist but no specific task was specified for resume: Glob, sort by `updated_at`, pick most recent. Print: "Resuming auto-mode task `<name>` from `<timestamp>`. Use `/auto --new <task>` to start fresh, `/auto --resume <task-name>` to resume a different one, or `/auto --list` to see all."

### What NOT to Do on Resume

- Do NOT blindly "continue working" without reading state
- Do NOT assume subagent results when session ended mid-wait
- Do NOT re-run destructive commands without checking if they already succeeded
- Do NOT skip phases because "we probably already did that"

## Completion Gates (Hard Gates Before Finishing)

These gates fire BEFORE entering the finishing phase. If any gate fails, auto-mode fixes and retries. Do NOT proceed to finishing until ALL gates pass.

### Gate 1: All Plan Tasks Executed

**Check:** Count plan tasks vs completed tasks in `progress.tasks_total` / `progress.tasks_completed`. If mismatch → execute remaining tasks.
**Timeout:** 10 fix iterations. Increment `gate_states.gate_1_tasks_executed.iterations` on each attempt.
**On failure:** Execute remaining tasks, re-check.

### Gate 2: All Per-Task Reviews Passed

**Scope:** Per-task reviews only (spec compliance + code quality for each task). Plan reviewer and final code reviewer are separate (Gate 5).

**Check:** For each task, verify spec reviewer returned ✅ AND code reviewer returned ✅. If any task has open review issues → fix → re-review.
**Reviewer loop:** 5-iteration limit per issue (see Reviewer Loop Limit in Phase 3).
**On failure:** Fix issues, re-run review.

### Gate 3: Test Suite Passes

**Check:** Run the project's test command (`pytest` or equivalent). Zero failures required.
**Timeout:** 10 fix iterations. Increment `gate_states.gate_3_tests_pass.iterations` on each attempt.
**On failure:** Fix failures, re-run. Loop until clean.

### Gate 4: Verification Against Spec

**Check:** Read spec document line by line. Verify each requirement exists in the codebase.
**Timeout:** 10 fix iterations. Increment `gate_states.gate_4_spec_verified.iterations` on each attempt.
**On failure:** Implement missing requirements → re-verify.

### Gate 5: Final Code Review Passed

**Check:** Dispatch final code reviewer subagent on the full implementation diff. Must return approved.
**Reviewer loop:** 5-iteration limit per issue.
**On failure:** Fix issues → re-review.

### Gate 6: Git Status Clean

**Check:** `git status --porcelain` must be empty.
**Timeout:** 10 fix iterations. Increment `gate_states.gate_6_git_clean.iterations` on each attempt.
**On failure:** Commit changes or clean up untracked files. Re-check.

### Gate Order

```
Gate 1: Tasks executed? ──No──→ Execute remaining tasks
    Yes ↓
Gate 2: Reviews passed? ──No──→ Fix → re-review (5-iteration limit)
    Yes ↓
Gate 3: Tests pass? ──No──→ Fix → re-run (10-iteration timeout)
    Yes ↓
Gate 4: Spec covered? ──No──→ Implement missing → re-verify (10-iteration timeout)
    Yes ↓
Gate 5: Final review? ──No──→ Fix → re-review (5-iteration limit)
    Yes ↓
Gate 6: Git clean? ──No──→ Commit or clean up
    Yes ↓
ENTER FINISHING PHASE
```

### Gate Iteration Tracking

- Gates 2 and 5 use reviewer loops → 5-iteration limit per issue (enforced by `reviewer_loop_iterations` in state.json)
- Gates 1, 3, 4, 6 track iterations in their `gate_states` entries (`gate_N_*.iterations`). 10-iteration gate timeout as backstop
- If any gate exceeds its limit, auto-mode stops with: which gate is stuck, what was attempted, what the user can do

## Stop Conditions (Only These)

Auto-mode ONLY stops and asks your human partner when:

1. **Requirements are genuinely ambiguous.** The task description could mean multiple, fundamentally different things and no reasonable default exists. Example: "optimize the system" — no context about what's slow.

   **Action:** Write `stopped_question` to state.json, set status `STOPPED_ASK_USER`, print the single focused question. Wait for answer.

2. **Platform/Infrastructure decision.** The task requires choosing a platform or infrastructure with high switching cost and no obvious default. Example: "deploy this" without knowing target (AWS vs Vercel vs self-hosted).

   **Action:** Same as #1 — single focused question, wait for answer.

3. **All BLOCKED-retry strategies exhausted.** Implementer stuck after trying: more capable model → smaller task → additional context. All 3 failed.

   **Action:** Present the blocker with context: which task, what was tried, what's needed. Wait for guidance.

4. **Reviewer loop iteration limit hit.** 5-iteration fix → re-review limit exceeded for any single reviewer issue.

   **Action:** Present the reviewer feedback and attempted fixes. Ask your human partner to resolve the contradiction or provide direction.

When auto-mode stops, it presents exactly what it needs — a single, focused question. After your human partner answers → update state.json → resume pipeline from where it stopped.

Everything else is auto-decided: naming, file structure, library choices, UI layout, testing strategy, error handling patterns, reviewer feedback, merge strategy.

## Worktree Lifecycle

Auto-mode follows the same worktree rules as normal execution:

1. **Before implementation:** Create or enter a worktree via `Skill("claude-code-flow:using-git-worktrees")` unless already in one. Record `worktree_path` in `state.json`.
2. **During finishing (merge back):** After successful merge, clean up the worktree if it was created by auto-mode — same provenance check as `finishing-a-development-branch`.
3. **On interruption:** Worktree persists. On resume, `state.json` tells auto-mode where the worktree is. Cd into it before continuing.

## Risk Mitigation

- **All commits are normal git commits.** Your human partner can `git revert` or `git reset` if unhappy.
- **Spec and plan documents are written to disk** (`.claude/specs/`, `.claude/plans/`) before implementation starts. Your human partner can review what auto-mode decided even after the fact.
- **Auto-mode announces decisions as it makes them.** Your human partner sees what's happening, can Ctrl+C to interrupt at any time.
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
- Skip writing to audit trail — every decision must be logged
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
