---
name: auto-mode
description: Fully automatic Claude Code Flow development mode. Use for /auto, 全自动模式, workflow execution, branch finalization, and image generation when needed.
---

# Auto Mode

Core: one autonomous Claude Code Flow entrypoint: discover → spec → plan → execute → review → verify → finalize. Auto-decide routine choices, log decisions, ask only when genuinely blocked.

Announce: “I'm using auto-mode to run the development workflow autonomously. Decisions and evidence will be logged under `.claude/auto/<task-name>/`. Ctrl+C to interrupt.”

## Use

Trigger on `/auto <task>`, `全自动模式 <task>`, `CCF_AUTO_MODE=1`, `/auto --resume`, `/auto --new`, `/auto --list`. Slash parsing is harness-owned.

**MANDATORY first step (before ANY implementation):**
1. Create `.claude/auto/<task-name>/state.json` IMMEDIATELY. This is non-negotiable — even for trivial one-file tasks. Without `state.json`, hooks cannot protect the pipeline, and interruption recovery is impossible. Write at minimum `{"task_name":"...","phase":"execute","status":"ACTIVE","updated_at":"..."}`.
2. Investigate existing code/patterns before implementation.
3. Write/review spec and plan; user approval is not required after `/auto` consent.
4. Execute via Dynamic Workflow when available: `workflows/full-auto-pipeline.workflow.js` owns parallel agents, reviews, retries, gates, and resume. Use direct implementation only for small safe tasks — but even direct implementation MUST create the audit trail first.
5. For plan-only execution, use `workflows/execute-plan.workflow.js` with parsed task groups.
6. Run review/fix loops, tests, runtime checks, and final gates.
7. Finalize locally: summarize, clean planned artifacts, report git state. No PR unless user explicitly asks and reviews the diff.
8. Write terminal state: `DONE`, `STOPPED_ASK_USER`, `FAILED_FATAL`, or `CANCELLED`.

No post-pass approval prompt: when all seven completion gates pass, do not ask whether to finish, commit, merge, or deliver. Proceed directly to final delivery.

## Auto Decisions

Clarifications → infer/log. Approach → existing patterns > project convention > minimal viable default. Spec/plan approval → reviewer loop. Branch completion → internal finalization phase. Apply YAGNI.

For UI/game tasks, use `2d-game-workflow.md` when relevant. For image/sprite/asset generation or image editing, use `image-generation.md`; dispatch artist work only when files are actually needed.

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
| 7 | `git_clean` | `git status --porcelain` empty after planned cleanup | 10 |

Runtime evidence manifest fields: `commands`, `exit_codes`, `logs`, `screenshots`, `artifacts`, `crash`, `hang`, `unverified_acceptance_items`, `blocking_risks`, `generated_at`.

Detailed audit contract: `audit-trail.md`. Dynamic Workflow owns execution state; keep local `state.json` only for resume/interruption recovery.

## State + Audit

### One Active Run Per Worktree

Only one non-terminal auto-mode run per workspace. Write `state.json` before transitions. Log choices under `.claude/auto/<task-name>/`. Use `flow-state.py`/`flowState` when available: `event` records audit events; `update` writes with `expected_revision`/`revision`. Resume via `resume_cursor`; do not blindly rerun complete phases. Cursor includes `gate_cursor`, `spec_path`, `plan_path`, `result_replay`.

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

Never skip/reorder gates; proceed with failing gate; ask outside stop conditions; ask after gates green; treat `git_clean` failure as a question; rerun destructive resume steps; claim generated image files before they exist; skip audit trail.
