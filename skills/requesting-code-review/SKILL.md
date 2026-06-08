---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

Dispatch a fresh reviewer with bounded context: changed work, requirements, exact diff range. Review product, not conversation history.

## When

Mandatory after each workflow task, major feature/bugfix, and before merge. Useful when stuck, before risky refactor, after complex bug fix.

Automated plans: use `claude-code-flow:workflow-driven-development`; it owns review/fix loops. This is the manual primitive.

## How

1. Identify range: `BASE_SHA=$(git rev-parse origin/main)` or task start SHA; `HEAD_SHA=$(git rev-parse HEAD)`.
2. Dispatch reviewer with `requesting-code-review/code-reviewer.md`.
3. Provide `{DESCRIPTION}`, `{PLAN_OR_REQUIREMENTS}`, `{BASE_SHA}`, `{HEAD_SHA}`.
4. Act: Critical/Important → fix before proceeding; Minor → cheap fix or note; wrong/unclear → push back with code/tests/evidence.

Bug/failing behavior in feedback → use `claude-code-flow:systematic-debugging` before fixing. Before success claims → `verification-before-completion`. For merge/PR/cleanup → `finishing-a-development-branch`.

## Red Flags

Never skip review because “small”; review without SHA range; give vague context; ignore Critical/Important; blindly apply questionable feedback.
