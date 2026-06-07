---
name: executing-plans
description: Inline fallback for trivial tasks (config-only, no logic) — workflow-driven-development is the default
---

# Executing Plans

Fallback path for trivial/config-only plans created by **claude-code-flow:writing-plans**, or harnesses without `Workflow`/subagents. For any non-trivial plan, use **claude-code-flow:workflow-driven-development** instead.

**Announce at start:** "I'm using the executing-plans skill as a fallback to implement this trivial plan inline."

## Use Only When

- Plan is config-only/docs-only/mechanical
- No new behavior or tests needed
- No parallel subtasks/review loop needed
- `Workflow` or subagents are unavailable

Otherwise: invoke **workflow-driven-development**.

## Process

1. Read the plan once.
2. Critically check for blockers, ambiguity, missing verification.
3. Create todos for plan tasks.
4. Execute tasks in order; follow each step exactly.
5. Run stated verification.
6. Before claiming done, invoke **claude-code-flow:verification-before-completion**.
7. If development branch needs integration/cleanup, invoke **claude-code-flow:finishing-a-development-branch**.

## Stop and Ask

Stop immediately when:

- Plan has critical gaps
- Instruction is unclear
- Dependency/tooling missing
- Verification fails repeatedly
- Task stops being trivial

Do not guess through blockers. Do not continue inline once the task needs workflow orchestration.

## Red Flags

Never:

- Use this to avoid workflow-driven-development for real implementation work
- Start implementation on main/master without explicit consent
- Skip verification because the change is small
- Continue after failed verification without diagnosing cause
