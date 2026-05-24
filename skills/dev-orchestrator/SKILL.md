---
name: dev-orchestrator
description: "Orchestrate dev work: implement, build, fix, refactor, test, review, ship, verify, finish branches, and coordinate agents. Use as default entry for most software tasks: implement, fix, build, refactor, test, execute an approved plan, multi-step delivery, or finish/verify work."
---

# Development Orchestrator

Route and execute software work through the project pipeline. Treat the orchestrator as the harness control plane: route requests, advance `.claude/flow/workflow-state.json`, dispatch isolated agents, enforce policy through hooks, and require `.claude/flow/verification-evidence.jsonl` before completion claims.

<SUBAGENT-STOP>
If dispatched as a subagent for a specific implementation task, skip routing and run the assigned task only.
</SUBAGENT-STOP>

## Routing

Run one routing pass unless a command, hook, or active skill already selected the path.

- Ambiguous product/architecture/UI direction - `brainstorming`.
- Explicit plan/spec/task breakdown - `planning`.
- Bug, crash, regression, failing test/build - `systematic-debugging`.
- Test strategy or requested tests-first design - `testing-strategy`.
- Review-only request - `code-review`.
- External workflow/repo/agent pack intake - `workflow-intake`.
- Otherwise execute here.

## Pipeline

Use plugin planning/routing; prefer `plan` and avoid `EnterPlanMode` for this workflow. Runtime plan state lives in `.claude/flow/plan-state.json`; workflow state lives in `.claude/flow/workflow-state.json`; plan handoff brief is `plan-brief.md`.

1. Define goal, assumptions, success criteria, and verification.
2. Inspect current state; protect unrelated user changes.
3. Prefer test-first for behavior changes.
4. Implement surgically.
5. Run focused verification.
6. Run review loop when changes are non-trivial.
7. Report changed files and fresh evidence only.

## Required References

Read as needed, not all upfront:

- `references/pipeline-operations.md` - gate checklist, order, acceptance.
- `references/parallel-dispatch.md` - when/how to use teams or subagents.
- `references/subagent-prompts.md` - prompt templates.
- `references/review.md` - review boundaries and fix loops.
- `references/verification-gate.md` - evidence standards.
- `references/finish-branch.md` - merge/PR/keep/discard decisions.
- `references/diagnostics.md` - runtime state and metrics.
