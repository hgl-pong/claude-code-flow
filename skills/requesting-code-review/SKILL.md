---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

Dispatch a fresh reviewer with bounded context: what changed, what it should satisfy, and the exact diff range. Do not hand over session history.

**Core principle:** Review work product, not the conversation.

## When

Mandatory:

- After each task in workflow-driven development
- After major feature/bugfix completion
- Before merge to main

Useful:

- When stuck
- Before risky refactor
- After fixing complex bug

For automated plan execution, use **claude-code-flow:workflow-driven-development**; it owns the review/fix loop. This skill is the manual review primitive.

## How

1. Identify diff range:

```bash
BASE_SHA=$(git rev-parse origin/main)  # or task start SHA
HEAD_SHA=$(git rev-parse HEAD)
```

2. Dispatch reviewer subagent with `requesting-code-review/code-reviewer.md`.

Required context:

- `{DESCRIPTION}` — concise summary of work
- `{PLAN_OR_REQUIREMENTS}` — spec/plan/acceptance criteria
- `{BASE_SHA}` — starting commit
- `{HEAD_SHA}` — ending commit

3. Act on feedback:

- Critical → fix before anything else
- Important → fix before proceeding/merge
- Minor → fix if cheap; otherwise note
- Wrong/unclear → push back with code/tests/evidence

If feedback reports a bug or failing behavior, use **claude-code-flow:systematic-debugging** before implementing the fix.

Before claiming done after fixes, use **claude-code-flow:verification-before-completion**. For merge/PR/cleanup choices, use **claude-code-flow:finishing-a-development-branch**.

## Red Flags

Never:

- Skip review because the change is small
- Review without a clear SHA range
- Give reviewer only vague context
- Ignore Critical/Important findings
- Blindly apply questionable feedback
