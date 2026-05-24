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

## Hard Stops Before Implementation

- If the request is vague or underspecified, ask clarifying questions before classification, planning, or implementation.
- If the request is a website, official site, landing page, docs site, design system website, multi-page UI, or broad UI outcome, it is never quick/lightweight: run clarification → research → plan → UI research/design as applicable before any code edits.
- For frontend-UI work in standard+ mode, do not dispatch forge or write code until UI Design Gate 6c has explicit user approval.

1. Define goal, assumptions, success criteria, and verification; if requirements are vague or underspecified, ask clarifying questions before classification or implementation.
2. Inspect current state; protect unrelated user changes.
3. Classify very lightweight vs non-trivial; default to non-trivial unless the request matches the lightweight whitelist in `references/pipeline-operations.md`.
4. Run research before plan for most work; treat research quality as outcome-critical.
5. Prefer test-first for behavior changes.
6. Classify direct vs agentic; implement directly only for very lightweight tasks.
7. For non-trivial work, dispatch bounded subagents and keep orchestration/final verification in the main conversation.
8. Run focused verification.
9. Run multi-round review for non-trivial work: sentinel findings become fix tasks, fixes are verified, then review repeats until approval or escalation.
10. Report changed files and fresh evidence only.

## Required References

Read as needed, not all upfront:

- `references/pipeline-operations.md` - gate checklist, order, acceptance.
- `references/parallel-dispatch.md` - when/how to use teams or subagents.
- `references/subagent-prompts.md` - prompt templates.
- `references/review.md` - review boundaries and fix loops.
- `references/verification-gate.md` - evidence standards.
- `references/finish-branch.md` - merge/PR/keep/discard decisions.
- `references/diagnostics.md` - runtime state and metrics.
