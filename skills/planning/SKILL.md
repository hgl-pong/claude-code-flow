---
name: planning
description: "Write and execute implementation plans with task breakdowns, approval gates, dependencies, and verification steps. Use for plan requests, feature planning, task creation, executing approved specs/plans, or turning requirements into implementation steps; skip simple fixes."
---

# Planning

Plans are executable documents, not chat summaries. This skill owns the plan artifact contract and task decomposition; entry routing, gate classification, and dispatch policy live in `skills/dev-orchestrator/references/pipeline-operations.md` and `parallel-dispatch.md`.

Before approval or implementation, every plan document MUST include `Local Research`, `External Research`, `Success Criteria`, `Verification`, and `Self Review Result` sections. If self-review finds missing requirements, vague tasks, missing file paths, unrunnable commands, or unresolved contradictions, revise the plan document and repeat self-review before dispatch.

Create executable plans; execute only after approval unless the user already approved the plan.

## Rules

- Never invent requirements.
- Every task must map to a requirement and a verification check.
- Plans must name files/areas to inspect, likely edits, tests, dependencies, and risks.
- Treat the context envelope as the source of truth for requirements, constraints, and approval state.
- Do not plan indefinitely; ask only blocking questions.

## Workflow

1. Clarify goal, constraints, non-goals, and success criteria.
2. Consume completed gate artifacts from `pipeline-operations.md` when they exist.
3. Write the plan document with Local Research, External Research, tasks, dependencies, and verification.
4. Run the plan document self-review loop; revise until `Self Review Result: PASS`.
5. Request approval.
6. On approval, hand execution to dev-orchestrator or execute the tasks with verification.

## Output

- Goal / decisions / assumptions
- Local Research
- External Research
- Ordered tasks and dependencies
- Verification commands and expected evidence
- Self Review Result
- Risks / open questions

## Executable Task Mapping

Every approved plan must show each requirement maps to at least one task with exact file scope, dependency edges, runnable verification command, and acceptance criterion. A plan cannot unblock implementation until its document self-review says Self Review Result: PASS.

## Dependency and Acceptance Matrix

Plans for non-lightweight work must include a dependency and acceptance matrix: task id, exact file scope, blockedBy edges, verification command, expected acceptance evidence, and owner role. No task may depend on a vague predecessor; split or rewrite any predecessor that does not produce a concrete artifact.
