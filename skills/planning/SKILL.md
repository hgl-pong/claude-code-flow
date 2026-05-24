---
name: planning
description: "Write and execute implementation plans with task breakdowns, approval gates, dependencies, and verification steps. Use for plan requests, feature planning, task creation, executing approved specs/plans, or turning requirements into implementation steps; skip simple fixes."
---

# Planning

Create executable plans; execute only after approval unless the user already approved the plan.

## Rules

- Never invent requirements.
- Every task must map to a requirement and a verification check.
- Plans must name files/areas to inspect, likely edits, tests, dependencies, and risks.
- Treat the context envelope as the source of truth for requirements, constraints, and approval state.
- Do not plan indefinitely; ask only blocking questions.

## Workflow

1. Clarify goal, constraints, non-goals, and success criteria.
2. Inspect code enough to ground the plan.
3. Break work into ordered tasks with dependencies.
4. Include RED/GREEN verification for behavior changes.
5. Request approval.
6. On approval, hand execution to dev-orchestrator or execute the tasks with verification.

## Output

- Goal / decisions / assumptions
- Ordered tasks and dependencies
- Verification commands and expected evidence
- Risks / open questions

