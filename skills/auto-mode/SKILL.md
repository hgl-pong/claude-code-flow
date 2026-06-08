---
name: auto-mode
description: Fully automatic development pipeline — brainstorming to merge, no user interaction. Trigger with /auto or 全自动模式
---

# Auto Mode

Run autonomously: `brainstorming → writing-plans → workflow-driven-development → completion gates → finishing-a-development-branch`.

Core: automate decisions, log decisions, stop only when genuinely blocked.

Announce: “I'm using the auto-mode skill to run the full development pipeline autonomously. All decisions will be logged to `.claude/auto/<task-name>/`. Ctrl+C to interrupt at any time.”

## Triggers

`/auto <task>`, `全自动模式 <task>`, `CCF_AUTO_MODE=1`, `/auto --resume [task-name]`, `/auto --new <task>`, `/auto --list`. Slash parsing is harness-owned.

## Required Skills

Invoke, don't restate: `claude-code-flow:using-git-worktrees`, `brainstorming`, `writing-plans`, `workflow-driven-development`, `finishing-a-development-branch`. Subagents use `test-driven-development`; reviewers use `requesting-code-review`.

## Workflow Mode

Preferred when `Workflow` exists.

1. Create/enter isolated worktree; record `worktree_path`.
2. Create `.claude/auto/<task-name>/state.json` immediately.
3. Run `skills/workflow-driven-development/full-auto-pipeline.workflow.js` with task/worktree/specs/plans/audit/evidence dirs, retry policy, `execute-plan.workflow.js`, state file, and flow-state helper path.
4. Inspect `result.all_passed` and `result.gates`.
5. If all passed, finish directly.
6. Write terminal state: `DONE`, `STOPPED_ASK_USER`, `FAILED_FATAL`, or `CANCELLED`.

No post-pass approval prompt: when all seven completion gates pass, Do not ask whether to finish, commit, merge, or deliver. The user already chose auto-mode. proceed directly to final delivery.

Manual fallback only if `Workflow` unavailable: brainstorm with logged defaults, write/review plan, use `executing-plans` only for trivial/config-only work, then gates + finish.

## Auto Decisions

Clarifications → infer/log. Visual companion → skip text-only/log. Approach → existing patterns > community standard > minimal viable. Spec/plan approval → reviewer loop. Finishing → default merge back to base branch. Apply YAGNI.

## Completion Gates

All must pass; retry until cap.

| # | Gate | Predicate | Retry |
|---|---|---|---|
| 1 | `tasks_executed` | all tasks completed; zero blocked | 10 |
| 2 | `reviews_passed` | spec + code reviewer passed every task | 5/issue |
| 3 | `tests_pass` | project test command exits zero failures | 10 |
| 4 | `runtime_evidence` | runnable smoke-tested; non-runnable auto-pass/unverifiable | 10 |
| 5 | `spec_verified` | spec requirements checked against code | 10 |
| 6 | `final_review` | full-diff final reviewer approved | 5/issue |
| 7 | `git_clean` | `git status --porcelain` empty after planned commits/cleanup | 10 |

Runtime evidence manifest fields: `commands`, `exit_codes`, `logs`, `screenshots`, `artifacts`, `crash`, `hang`, `unverified_acceptance_items`, `blocking_risks`, `generated_at`.

Detailed schemas: `references/state-machine.md`, `references/audit-trail.md`.

## State + Audit

### One Active Run Per Worktree

Only one non-terminal auto-mode run per worktree.

Write `state.json` before transitions. Log choices under `.claude/auto/<task-name>/`. Use `flow-state.py`/`flowState` when available: `event` records audit events; `update` writes with `expected_revision`/`revision`. Resume via `resume_cursor`; do not blindly rerun complete phases. Cursor includes `gate_cursor`, `spec_path`, `plan_path`, `result_replay`. Preserve worktree on interruption.

## Finalization Rule

Auto-mode finalizes autonomously. After all seven completion gates pass, proceed directly to final delivery and write `DONE`. Do not ask for another approval/status step.

Commit before git_clean when changes are part of the task and checks passed. Gate 7 validates; it is not a question. If harness blocks commit/merge, write `STOPPED_ASK_USER` with exact command and one recovery question.

## Stop Conditions

Ask exactly one focused question only for: fundamentally different requirements; high-cost platform choice with no default; exhausted recovery; reviewer loop >5 for one issue; gate retry cap exceeded. Everything else is auto-decided/logged.

## Final Summary

```text
Auto-mode complete. Decision trail at .claude/auto/<task-name>/
  Status: <DONE | STOPPED_ASK_USER | FAILED_FATAL | CANCELLED>
  Tasks: <summary>
  Gates: <gate_cursor>/7 passed
  state_file: .claude/auto/<task-name>/state.json
  evidence_dir: .claude/auto/<task-name>/evidence/
  audit_events: <count>
  resume_cursor: <cursor>
  Review: .claude/auto/<task-name>/decisions.md
```

## Red Flags

Never start implementation on main/master without isolated worktree; skip/reorder gates; proceed with failing gate; ask outside stop conditions; ask after gates green; treat `git_clean` failure as a question; rerun destructive resume steps; modify existing skill files as auto-mode output; skip audit trail.
