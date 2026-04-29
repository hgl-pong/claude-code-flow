---
name: Writing Plans
version: "1.0.0"
description: Use after requirements or a design are approved and before executing a multi-step implementation.
---

# Writing Plans

Create an implementation plan that a fresh agent can execute without guessing. Plans should be small, concrete, test-first, and easy to review.

## Plan Location

Save substantial plans to:

`docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`

## Required Header

Every plan starts with:

```markdown
# <Feature Name> Implementation Plan

**Goal:** <one sentence>
**Architecture:** <2-3 sentence summary>
**Verification:** <main commands and acceptance checks>
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
- Each task should normally take 2-15 minutes.
- Prefer fewer abstractions until duplication or complexity proves the need.

## Self-Review

Before execution:

1. Map each requirement to at least one task.
2. Search for placeholders and vague instructions.
3. Check type names, function names, command names, and file paths for consistency.
4. Confirm task order respects dependencies.

## Handoff

For execution, use the orchestrator's subagent-driven loop when tasks are independent. Use inline execution when tasks are tightly coupled or require continuous local context.
