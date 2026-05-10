# Plan Quality Reference

## Plan Location

Persist the authoritative plan in structured workflow state first:

- `.claude/flow/plan-state.json`
- `.claude/flow/workflow-state.json`

Export `.claude/flow/plans/<task-slug>/plan-brief.md` only as the agent-readable brief when needed. Always pass the full slug path explicitly: `flow-state.py plan-approve --output .claude/flow/plans/<task-slug>/plan-brief.md`
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

## Task Shape

Each task should be independently understandable. Annotate `agent:` and `blockedBy:` so the orchestrator can build the dispatch DAG without guessing.

```markdown
### Task N: <name>

**Agent:** forge | prism | sentinel | research
**BlockedBy:** [task IDs] | none
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

**Agent assignment rules:**
- `forge` — any file creation/modification
- `prism` — test runs, build verification, acceptance checks
- `sentinel` — review only; always after prism; never writes code
- `research` — research subagent (general-purpose + research skill); analysis, doc reading; writes only analysis output files

**BlockedBy rules:** only add a true data dependency. "Task B needs Task A's output file" → blocked. "Task B is in the same module" → NOT a reason to block; check for file conflict instead.

## Quality Bar

- Exact file paths.
- Exact commands.
- Expected output for tests that should fail or pass.
- No placeholders.
- No "similar to previous task"; repeat the needed details.
- Each task has one verification command that proves it done. If you can't write a single command, the task needs to be split.
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

The source of truth is the approved plan/spec plus `<output_dir>/phase-context.md` and `<output_dir>/plan-brief.md`; do not rely on chat history for implementation details.
