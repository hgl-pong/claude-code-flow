---
name: Writing Plans
version: "1.0.0"
description: "Use for: creating implementation plans from approved designs, task breakdown with test-first structure."
---

# Writing Plans

## IRON LAW

**NO PLACEHOLDERS. NO VAGUE INSTRUCTIONS. EVERY TASK STANDS ALONE.**

A plan is written for a fresh agent with zero project context, zero judgment, and zero ability to "figure it out." If a task cannot be executed by reading it alone, the plan is incomplete.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The developer can figure it out" | If they could, they wouldn't need a plan. Be explicit. |
| "Similar to the previous task" | Similar is not identical. Repeat the details. |
| "I'll add TODOs for the tricky parts" | TODOs in a plan mean the plan is not done. Resolve them now. |
| "The file path is obvious from context" | Context is what the plan creates. Write every path explicitly. |

### Red Flags — STOP if you catch yourself thinking:

- "They'll know what I mean"
- "I'll skip the test command, it's standard"
- "I'll just reference the design doc"
- "The exact file doesn't matter at this stage"

## Plan Location

Persist the authoritative plan in structured workflow state first:

- `.claude/flow/plan-state.json`
- `.claude/flow/workflow-state.json`

Export `.claude/flow/plan-brief.md` only as the agent-readable brief when needed.
Never treat `docs/` as the source of truth for plan state.

## Required Header

Every plan starts with:

```markdown
# <Feature Name> Implementation Plan

**Goal:** <one sentence>
**Architecture:** <2-3 sentence summary>
**Verification:** <main commands and acceptance checks>

## Decisions
- <decision>: <rationale>

## Rejected Alternatives
- <alternative>: <why rejected>

## Risks
- <risk>: <mitigation>
```

## Process

1. Read the approved spec or requirements.
2. Map files to responsibilities.
3. Split work into small test-first tasks.
4. Add exact commands and expected results.
5. Run the self-review checklist before handoff.

## Task Shape

Each task should be independently understandable:

```markdown
### Task N: <name>

**Files:**
- Create: `path/to/new-file`
- Modify: `path/to/existing-file`
- Test: `path/to/test-file`

- [ ] Step 1: Write the failing test
  - Command: `<exact test command>`
  - Expected failure: `<specific failure>`
- [ ] Step 2: Implement the smallest change
- [ ] Step 3: Run focused tests
- [ ] Step 4: Run broader verification if needed
- [ ] Step 5: Review and record evidence
```

## Quality Bar

- Exact file paths.
- Exact commands.
- Expected output for tests that should fail or pass.
- No placeholders.
- No "similar to previous task"; repeat the needed details.
- Each implementation task should normally take 2-5 minutes; split anything larger into test, implementation, and verification tasks.
- Prefer fewer abstractions until duplication or complexity proves the need.

## Self-Review

Before execution:

1. Map each requirement to at least one task.
2. Search for placeholders and vague instructions.
3. Check type names, function names, command names, and file paths for consistency.
4. Confirm task order respects dependencies.

## Handoff

For execution, use the orchestrator's subagent-driven loop when tasks are independent. Use inline execution when tasks are tightly coupled or require continuous local context.

Every task handed to `dev-orchestrator` must be convertible into the orchestrator context envelope: goal, exact task, working directory, completed dependencies, file scope, test command, acceptance criteria, relevant excerpts, constraints, and out-of-scope boundaries. If any field is missing, keep planning instead of dispatching an implementation agent.

The source of truth is the approved plan/spec plus `phase-context.md` and `plan-brief.md`; do not rely on chat history for implementation details.
