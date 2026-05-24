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

- Broad, high-impact, multi-step, cross-domain, unfamiliar, quality-sensitive, or outcome-oriented requests without exact implementation scope - `/plan`.
- Ambiguous product/architecture/UI direction that is not broad outcome work - `brainstorming`.
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
- If the request is not very lightweight, the main conversation must not produce a chat-only proposal or task list as a substitute for the workflow.
- For every task that is not very lightweight, the main conversation controls the pipeline and MUST dispatch planning-stage subagents: general-purpose research first, oracle planning second, then applicable domain/UI design. Each subagent must produce its artifact and self-review it before the next gate consumes it.
- If the request is broad, high-impact, multi-step, cross-domain, unfamiliar, quality-sensitive, or outcome-oriented without exact implementation scope, it is never quick/lightweight: run clarification → research subagent → oracle plan → applicable domain design before any code edits.
- Frontend/UI/site work is one example of that rule: use UI research/design gates when applicable, and do not dispatch forge or write code until UI Design Gate 6c has explicit user approval.

1. Define goal, assumptions, success criteria, and verification; if requirements are vague or underspecified, ask clarifying questions before classification or implementation.
2. Inspect current state; protect unrelated user changes.
3. Classify very lightweight vs non-trivial; default to non-trivial unless the request matches the lightweight whitelist in `references/pipeline-operations.md`.
4. For non-trivial work, create planning-stage tasks and dispatch bounded subagents for research, oracle planning, and applicable design; do not collapse those gates into main-conversation prose.
5. Verify each research/plan/design artifact has detailed self-review PASS before the next gate consumes it.
6. Prefer test-first for behavior changes after plan/design approval.
7. Classify direct vs agentic; implement directly only for very lightweight tasks.
8. For non-trivial implementation, dispatch bounded subagents and keep orchestration/final verification in the main conversation.
9. Run focused verification.
10. Run multi-round review for non-trivial work: sentinel findings become fix tasks, fixes are verified, then review repeats until approval or escalation.
11. Report changed files and fresh evidence only.

## Required References

Read as needed, not all upfront:

- `references/pipeline-operations.md` - gate checklist, order, acceptance.
- `references/parallel-dispatch.md` - when/how to use teams or subagents.
- `references/subagent-prompts.md` - prompt templates.
- `references/review.md` - review boundaries and fix loops.
- `references/verification-gate.md` - evidence standards.
- `references/finish-branch.md` - merge/PR/keep/discard decisions.
- `references/diagnostics.md` - runtime state and metrics.
