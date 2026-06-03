---
name: auto-mode
description: Fully automatic development pipeline — brainstorming to merge, no user interaction. Trigger with /auto or 全自动模式
---

# Auto Mode

## Overview

Run the full Claude Code Flow pipeline — brainstorming → writing-plans → workflow-driven-development → finishing — without user interaction. Completion gates run between workflow-driven-development and finishing (tracked as a separate state-machine phase for recovery).

**Core principle:** Automate every decision. Log everything. Never stop unless truly stuck.

**Announce at start:** "I'm using the auto-mode skill to run the full development pipeline autonomously. All decisions will be logged to `.claude/auto/<task-name>/`. Ctrl+C to interrupt at any time."

## Execution Mode Selection

Before entering the pipeline, check whether the `Workflow` tool is available.

### Workflow-Driven Mode (preferred, when available)

When the Workflow tool is available, replace all 4 phases with a single workflow call.
The workflow handles brainstorming, writing-plans, workflow-driven-development,
and completion gates in one deterministic run. Your job shrinks to:

1. Create or enter a worktree via `Skill("claude-code-flow:using-git-worktrees")`
2. Create `.claude/auto/<task-name>/` and write initial `state.json`
3. Read the workflow scripts (self-contained — prompts are embedded):
   - `skills/workflow-driven-development/full-auto-pipeline.workflow.js`
   - `skills/workflow-driven-development/execute-plan.workflow.js`
4. Build the args:
   - `task` — the user's task description
   - `worktree` — absolute path to worktree
   - `specs_dir` — `".claude/specs"`
   - `plans_dir` — `".claude/plans"`
   - `auto_dir` — `".claude/auto/<task-name>"`
   - `execute_plan_script_path` — absolute path to `execute-plan.workflow.js`
   - `model_tasks` — `null` or model name
   - `max_retries` — `5`
5. Launch:
   ```
   Workflow({ script: <full-auto-pipeline.workflow.js>, args: {...} })
   ```
6. When complete, inspect `result.all_passed`:
   - `true` → proceed to **Phase 4: Finishing** below
   - `false` → check `result.gates` for which gate failed, handle individually
7. Write final `state.json` with status `DONE`

The state machine simplifies to three states: `WORKFLOW_RUNNING` → `FINISHING` → `DONE`.
No more per-phase state tracking, no manual pool management, no gate loops.

### Manual Mode (fallback)

When the Workflow tool is NOT available, use the manual pipeline below.

## State Writer Handoff

When running in workflow-driven mode, the full-auto-pipeline delegates state management to `flow-state.py` via the `flowState` helper:

```
flowState(cmd, payload) → workflow({ scriptPath: flowStateScriptPath }, { command, state_file, payload_json, expected_revision })
```

- `cmd='event'` — record a phase or audit event (e.g., `phase_start`, `run_complete`)
- `cmd='update'` — write a state update with optimistic concurrency via `expected_revision`
- The helper returns `{ ok: true, revision: N }` on success
- If `flow_state_script_path` is not provided, the helper is a no-op
- Revision tracking prevents lost updates: if `expected_revision` does not match the current state file revision, the write fails

The state file path (`state_file` arg) is `.claude/auto/<task-name>/state.json`. The audit directory (`audit_dir` arg) is `.claude/auto/<task-name>/`.

Full state schema, phase enums, and status values: see `references/state-machine.md`.

## Trigger Mechanism

1. `/auto <task description>` — start a new auto-mode pipeline
2. `全自动模式 <task description>` — natural language equivalent
3. `CCF_AUTO_MODE=1` in environment — session-persistent; any task triggers auto-mode, and on session start auto-resumes the most recent dangling task if `.claude/auto/*/state.json` files exist
4. `/auto --resume [task-name]` — resume most recent dangling task, or a specific one by name
5. `/auto --new <task>` — start fresh even if old state.json exists (old audit trail preserved)
6. `/auto --list` — list all dangling auto-mode tasks with status, updated_at, task_name

**Slash parsing is harness-owned:** The `/auto` commands above are convention-level triggers documented here for hook-level awareness. Actual slash parsing depends on the harness (Claude Code CLI, IDE, etc.). When the harness does not support slash commands, use the environment variable trigger or natural language instead.

**Conflict detection:** If your human partner says `/auto <new-task>` while `.claude/auto/*/state.json` files exist, print a warning listing the dangling task(s) and ask: resume old, start new anyway, or cancel.

## One Active Run Per Worktree

Only one auto-mode run may be active in a given worktree at a time. If a state file exists at `.claude/auto/<task-name>/state.json` with a non-terminal status (`ACTIVE`, `PAUSED_COMPACTING`, `BLOCKED_ESCALATING`, `DECIDING`, `AWAITING_SUBAGENTS`, `AWAITING_SHELL`, `EXECUTING_GATE`, `FINISHING`), a new `/auto` invocation must print a warning and offer to resume or cancel. Terminal statuses (`DONE`, `STOPPED_ASK_USER`, `FAILED_FATAL`, `CANCELLED`) do not block new runs.

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

### Phase 3: Workflow-Driven Development

Invoke `Skill("claude-code-flow:workflow-driven-development")` with the plan.

**Parallelism:** The Workflow runtime handles concurrency automatically (up to 16 agents). Build dependency graph from `plan.tasks[].depends_on` and pass topological groups to the workflow. Review chain per task (spec → code quality) runs within the pipeline. Track progress in `task_states{}` within `state.json`.

| Situation | Normal Mode | Auto Mode |
|-----------|-------------|-----------|
| Dispatch phase | Build dependency graph, pass topological groups to workflow | Same as normal + write `state.json` with `status: AWAITING_SUBAGENTS`, populate `task_states{}`. |
| Implementer DONE_WITH_CONCERNS | Read concerns, address if correctness/scope, proceed | Auto-read concerns. If correctness/scope issues: address, log, re-dispatch. If observations only: note and proceed to review. |
| Implementer NEEDS_CONTEXT | Search codebase, infer context, re-dispatch. Ask user if still ambiguous. | Auto-search codebase, infer context, re-dispatch with additional info. Log to `decisions.md`. |
| Implementer BLOCKED | Try in order: (1) more capable model, (2) smaller task, (3) additional context. Escalate if all fail. | Same + log each attempt. Only stop if all 3 fail. |
| Subagent completion | Fire next step for that task immediately (review chain). Fill vacant pool slots with dispatchable tasks. If pool empty and all agents done, proceed to completion gates. | Same as normal + update `active_agents[]` and `task_states{}` in state.json. |
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

These gates fire BEFORE entering the finishing phase. If any gate fails, auto-mode fixes and retries. Do NOT proceed to finishing until ALL gates pass. Gates use the canonical names from the implementation (not numbered).

| # | Gate Name | Predicate | Retry Cap |
|---|-----------|-----------|-----------|
| 1 | `tasks_executed` | All tasks completed, zero blocked (`blocked.length === 0`) | 10 iterations |
| 2 | `reviews_passed` | Spec reviewer and code reviewer passed for every completed task | 5 iterations/issue |
| 3 | `tests_pass` | Project test command exits with zero failures | 10 iterations |
| 4 | `runtime_evidence` | For runnable deliverables: build/run smoke path succeeds, exit code is zero, no crash/hang detected, evidence manifest generated, acceptance items checked or recorded, no blocking runtime risk. For non-runnable: auto-pass. | 10 iterations |
| 5 | `spec_verified` | Read spec line by line, verify each requirement in codebase | 10 iterations |
| 6 | `final_review` | Dispatch final reviewer on full diff, must return approved. If execute phase already produced a valid final review, reuse it. | 5 iterations/issue |
| 7 | `git_clean` | `git status --porcelain` empty (validation-only, does NOT instruct commit) | 10 iterations |

Tasks are not complete until they have:
- passing tests where applicable
- at least one real runtime smoke result where applicable
- evidence artifacts on disk at `.claude/deliverables/<task-name>/` for runnable deliverables
- acceptance items either checked or explicitly marked unverified
- known limitations explicitly recorded if anything remains unverified
- no blocking runtime risk remaining

**Gate order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → enter finishing. Each gate must pass before the next begins.

Gates 2 and 6 use reviewer loops (5-iteration limit per issue, tracked in `reviewer_loop_iterations`). Gates 1, 3, 4, 5, 7 track iterations in `gate_states` entries (10-iteration timeout as backstop). If any gate exceeds its limit, auto-mode stops with: which gate is stuck, what was attempted, what the user can do.

Runtime verification produces a structured manifest for Gate 4:

```json
{
  "commands": "<commands that were run>",
  "exit_codes": [0],
  "logs": [],
  "screenshots": [],
  "artifacts": [],
  "crash": false,
  "hang": false,
  "unverified_acceptance_items": [],
  "blocking_risks": [],
  "generated_at": "<ISO 8601>"
}
```

## Resume Cursor Mapping

When resuming a run, the `resume_cursor` from the previous run's result determines where to continue:

| Cursor Field | Maps To | Resume Behavior |
|-------------|---------|-----------------|
| `phase` | `PHASE_ORDER` index | Skip all phases with index less than `phase_index` |
| `phase_index` | Integer | Fast comparison for phase skip |
| `gate_cursor` | 0-7 | Skip gates 0 through `gate_cursor - 1`. Gate records from `gate_states` are preserved. |
| `gate_states` | Map of gate name to `{passed: bool}` | Used to validate that previously-passed gates are still valid (git log check) |
| `spec_path` | File path | Skip research and synthesize phases if spec exists on disk |
| `plan_path` | File path | Skip plan writing if plan exists on disk |
| `result_replay` | Task ID array | Skip re-execution of tasks that already passed. These tasks appear in `results.passed` directly. |

Resume flow:
1. Read `state.json` from `.claude/auto/<task-name>/`
2. Check `status` — if terminal, nothing to do
3. Use `resume_cursor` to determine skip points
4. Set `current_phase` and `current_step` from cursor
5. Do NOT re-check gates where `gate_cursor` indicates they passed
6. Do NOT re-execute tasks in `result_replay`
7. Write `state.json` before every subsequent state change

## Runtime Unverifiable Rules

Not all deliverables can be verified at runtime. The pipeline handles unverifiable cases:

- **Non-runnable deliverables** (documentation, config, static assets): Gate 4 auto-passes. `runtime_verification.status` is set to `unverifiable` rather than `passed`.
- **Tasks with `runtime_evidence_required: "not_needed"`**: The runtime evidence gate is skipped for these tasks. They still pass through all other gates.
- **Partially verifiable deliverables**: If some acceptance items cannot be verified at runtime, they are recorded in `unverified_acceptance_items` in the evidence manifest. These are non-blocking as long as no `blocking_risks` remain.
- **Smoke test timeout**: If a smoke test times out, `hang` is set to `true` in the manifest and the gate fails with `next_action: "fix_runtime"`.

A task is not complete until it has:
- passing tests where applicable
- at least one real runtime smoke result where applicable (or `runtime_evidence_required: "not_needed"`)
- evidence artifacts on disk at `.claude/auto/<task-name>/evidence/` for runnable deliverables
- acceptance items either checked or explicitly recorded in `unverified_acceptance_items`
- known limitations explicitly recorded if anything remains unverified
- no blocking runtime risk remaining

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

## Final Summary Disclosure

When auto-mode finishes, it discloses:

```
Auto-mode complete. Decision trail at .claude/auto/<task-name>/
  Phase: <final phase>
  Status: <DONE | STOPPED_ASK_USER | FAILED_FATAL | CANCELLED>
  Tasks: N total, M passed, X blocked, Y failed_review, Z needs_escalation
  Gates: <gate_cursor>/7 passed
  Clarifying questions auto-answered: N
  Approaches evaluated: M
  User interruptions: 0
  Audit events: K

  State file: .claude/auto/<task-name>/state.json
  Evidence dir: .claude/auto/<task-name>/evidence/
  Review: cat .claude/auto/<task-name>/decisions.md
  Revert: git revert <merge-commit>
```

The final return from `full-auto-pipeline.workflow.js` includes these fields:
- `state_file` — path to the state file
- `audit_events` — array of all recorded events
- `evidence_dir` — path to evidence directory
- `resume_cursor` — cursor for mid-pipeline resumption (contains `phase`, `gate_cursor`, `gate_states`, `spec_path`, `plan_path`, `result_replay`)

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
- **claude-code-flow:workflow-driven-development** — Phase 3: execute plan tasks
- **claude-code-flow:finishing-a-development-branch** — Final phase: merge and cleanup
- **claude-code-flow:using-git-worktrees** — Worktree creation and management
- **claude-code-flow:requesting-code-review** — Code review template for reviewer subagents

**Subagents use:**
- **claude-code-flow:test-driven-development** — Subagents follow TDD for each task
