---
name: auto-mode
description: Fully automatic development pipeline — brainstorming to merge, no user interaction. Trigger with /auto or 全自动模式
---

# Auto Mode

Run the full Claude Code Flow pipeline without user interaction:

`brainstorming → writing-plans → workflow-driven-development → completion gates → finishing-a-development-branch`

**Core principle:** Automate every decision, log every decision, stop only when genuinely blocked.

**Announce at start:** "I'm using the auto-mode skill to run the full development pipeline autonomously. All decisions will be logged to `.claude/auto/<task-name>/`. Ctrl+C to interrupt at any time."

## Trigger Mechanism

1. `/auto <task description>` — start a new auto-mode pipeline
2. `全自动模式 <task description>` — natural-language equivalent
3. `CCF_AUTO_MODE=1` — session-persistent; tasks trigger auto-mode, SessionStart can resume dangling `.claude/auto/*/state.json`
4. `/auto --resume [task-name]` — resume dangling task
5. `/auto --new <task>` — start fresh even if old state exists
6. `/auto --list` — list dangling auto-mode tasks

Slash parsing is harness-owned. If slash commands are unavailable, use env var or natural language trigger.

## Required Skills

Invoke these instead of restating their workflows:

- **claude-code-flow:using-git-worktrees** — create/enter isolated worktree; record `worktree_path`
- **claude-code-flow:brainstorming** — infer clarifications, choose simplest viable approach, write spec
- **claude-code-flow:writing-plans** — write/review implementation plan
- **claude-code-flow:workflow-driven-development** — execute plan via Dynamic Workflow
- **claude-code-flow:finishing-a-development-branch** — final merge/PR/cleanup path

Subagents follow **claude-code-flow:test-driven-development**. Reviewer prompts use **claude-code-flow:requesting-code-review**.

## Workflow-Driven Mode

Preferred when `Workflow` exists.

1. Create/enter worktree via **using-git-worktrees**.
2. Create `.claude/auto/<task-name>/state.json` immediately.
3. Run `skills/workflow-driven-development/full-auto-pipeline.workflow.js` with args for task, worktree, specs/plans dirs, audit/evidence dirs, retry policy, and `execute-plan.workflow.js` path.
4. Inspect `result.all_passed` and `result.gates`.
5. If all passed, use **finishing-a-development-branch** and proceed directly to final delivery.
6. Write final state: `DONE`, `STOPPED_ASK_USER`, `FAILED_FATAL`, or `CANCELLED`.

No post-pass approval prompt: when all seven completion gates pass, Do not ask whether to finish, commit, merge, or deliver. The user already chose auto-mode. Continue until final summary unless a Stop Condition applies.

The workflow owns phase execution, task dispatch, review/fix loops, retry handling, and completion gates. Do not duplicate manual pool/state management.

## Manual Mode Fallback

Only when `Workflow` is unavailable.

1. Use **brainstorming**; auto-answer gates with logged defaults.
2. Use **writing-plans**; auto-resolve only non-fundamental ambiguity.
3. Use **executing-plans** only for trivial/config-only work; otherwise stop and report Workflow unavailable.
4. Run completion gates below.
5. Use **finishing-a-development-branch**.

## Auto Decisions

At normal user gates:

- Clarifications → infer from task + project context; log to `clarifications.md`
- Visual companion → skip text-only; log to `decisions.md`
- Approach choice → existing patterns > community standard > minimal viable approach; log to `approaches.md`
- Spec/plan approval → reviewer loop until approved; log approval
- Finishing option → default to Option 1: merge back to base branch

Decision rules: YAGNI, smallest working scope, existing conventions, no speculative features.

## Completion Gates

Run before finishing. All must pass; each failure triggers fix/retry until cap.

| # | Gate Name | Predicate | Retry Cap |
|---|-----------|-----------|-----------|
| 1 | `tasks_executed` | All tasks completed; zero blocked | 10 |
| 2 | `reviews_passed` | Spec + code reviewer passed for every task | 5/issue |
| 3 | `tests_pass` | Project test command exits with zero failures | 10 |
| 4 | `runtime_evidence` | Runnable deliverables smoke-tested; non-runnable auto-pass/unverifiable | 10 |
| 5 | `spec_verified` | Spec requirements checked against code | 10 |
| 6 | `final_review` | Full-diff final reviewer approved | 5/issue |
| 7 | `git_clean` | `git status --porcelain` empty after planned commits/cleanup | 10 |

Runtime evidence manifest fields: `commands`, `exit_codes`, `logs`, `screenshots`, `artifacts`, `crash`, `hang`, `unverified_acceptance_items`, `blocking_risks`, `generated_at`.

Full schema/status/resume details live in `references/state-machine.md`; audit file formats live in `references/audit-trail.md`.

## State + Audit

### One Active Run Per Worktree

Only one non-terminal auto-mode run may be active per worktree.

- Write `state.json` before every state transition.
- Log every auto-choice to `.claude/auto/<task-name>/`.
- Use optimistic revision writes via `flow-state.py`/`flowState` when available: `event` records audit events, `update` writes state with `expected_revision`/`revision` tracking.
- On resume, use `resume_cursor`; do not re-run completed phases/tasks blindly.
- Cursor fields include `gate_cursor`, `spec_path`, `plan_path`, and `result_replay`.
- Preserve worktree on interruption; resume from recorded `worktree_path`.

## Finalization Rule

Auto-mode means finalization is autonomous. After all seven completion gates pass, proceed directly to final delivery and write `DONE`. Do not ask for another approval step, status check, or "should I continue?" confirmation.

Commit before git_clean when changes are part of the auto-mode task and tests/reviews have passed. Gate 7 verifies the result; it is not a reason to stop and ask. If the harness blocks commit/merge, record `STOPPED_ASK_USER` with the exact blocked command and one focused recovery question.

## Stop Conditions

Stop and ask exactly one focused question only when:

1. Requirements have multiple fundamentally different meanings and no reasonable default.
2. Platform/infrastructure choice has high switching cost and no obvious default.
3. BLOCKED recovery exhausted: stronger model → split task → enriched context.
4. Reviewer loop exceeds 5 iterations for one issue.
5. Gate retry cap exceeded.

Everything else is auto-decided and logged.

## Final Summary

Report:

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

Never:

- Start implementation on main/master without an isolated worktree
- Skip or reorder completion gates
- Proceed to finishing with any gate failing
- Ask the human partner outside stop conditions
- Ask for post-pass approval after gates are green
- Treat `git_clean` failure as a question instead of committing/cleaning planned task changes
- Re-run destructive resume steps without checking prior success
- Modify existing skill files as part of auto-mode output
- Skip audit trail writes
