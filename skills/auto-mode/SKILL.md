---
name: auto-mode
description: Fully automatic Claude Code Flow development mode. Use for /auto, 全自动模式, workflow execution, branch finalization, and image generation when needed.
---

# Auto Mode

**CRITICAL — READ FIRST:** This is not a normal skill. You are the orchestrator, not the implementer. Your job is to invoke the Dynamic Workflow system (`Workflow()`), which spawns subagents, runs reviews, checks gates, and manages state. The ONLY time you implement directly is a single-file, no-test, no-dependency triviality. If the task needs more than ONE file: invoke Workflow. If the task needs tests: invoke Workflow. If you are unsure: invoke Workflow.

With that understood: one autonomous Claude Code Flow entrypoint: discover → spec → plan → execute → review → verify → finalize. Auto-decide routine choices, log decisions, ask only when genuinely blocked.

Announce: “I'm using auto-mode to run the development workflow autonomously. Decisions and evidence will be logged under `.claude/auto/<task-name>/`. Ctrl+C to interrupt.”

## Use

Trigger on `/auto <task>`, `全自动模式 <task>`, `CCF_AUTO_MODE=1`, `/auto --resume`, `/auto --new`, `/auto --list`. Slash parsing is harness-owned.

**MANDATORY first step (before ANY implementation):**
1. Create `.claude/auto/<task-name>/state.json` IMMEDIATELY. This is non-negotiable — even for trivial one-file tasks. Without `state.json`, hooks cannot protect the pipeline, and interruption recovery is impossible. Write at minimum `{"task_name":"...","phase":"execute","status":"ACTIVE","updated_at":"..."}`.
2. Investigate existing code/patterns before implementation.

### Execution Path Selection — CRITICAL

The Dynamic Workflow system (`full-auto-pipeline.workflow.js`) exists specifically to sustain long-running autonomous work through parallel subagents, structured review loops, completion gates, and interruption recovery. **You MUST use it unless the task is genuinely trivial.**

**Use `Workflow({ scriptPath: "<plugin>/skills/auto-mode/workflows/full-auto-pipeline.workflow.js", args: {...} })` when the task requires ANY of:**
- Multiple files (3+) to implement
- Multiple subagents needed for parallel work
- Any dependency on existing project code
- User-facing features or backend services
- Tests that must pass before completion
- A spec or plan worth writing down
- Work that would take a human more than 5 minutes

**Direct implementation is ONLY acceptable when ALL of these are true:**
- Single file, single concern (e.g., "create Readme.md", "add a one-line config change")
- Zero dependencies on project architecture
- No tests needed
- No subagents needed
- Truly obvious what to do with zero design decisions

**Workflow invocation pattern:**
```
Workflow({
  scriptPath: "<skills_dir>/auto-mode/workflows/full-auto-pipeline.workflow.js",
  args: {
    task: "<user's task description>",
    worktree: "<current worktree path>",
    specs_dir: ".claude/specs",
    plans_dir: ".claude/plans",
    state_file: ".claude/auto/<task-name>/state.json",
    audit_dir: ".claude/auto/<task-name>/audit",
    evidence_dir: ".claude/auto/<task-name>/evidence",
    flow_state_cli_path: "<plugin>/hooks/scripts/flow-state.py",
    allow_commit: true,
    model_tasks: { default: "sonnet" },
    max_retries: 5,
  }
})
```

If you find yourself writing more than 3 files, STOP — you should have used the workflow. Restart with Workflow invocation.

**When workflow completes:** it returns `{ state_file, audit_events, evidence_dir, resume_cursor }`. Update local `state.json` with terminal status. Skip to final summary.

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
  Runtime evidence: <commands>; <playtest observation>; artifacts: <screenshots/logs/artifacts or none>; unverified: <refs or none>
```

## Red Flags

**YOU ARE THE ORCHESTRATOR, NOT THE IMPLEMENTER.** If you find yourself writing code directly (via Edit/Write tools) for more than a single trivial file, you are doing it wrong. Stop immediately and invoke `Workflow({ scriptPath: ".../full-auto-pipeline.workflow.js", args: {...} })` instead.

Never skip/reorder gates; proceed with failing gate; ask outside stop conditions; ask after gates green; treat `git_clean` failure as a question; rerun destructive resume steps; claim generated image files before they exist; skip audit trail; implement multi-file tasks directly instead of using Workflow.
