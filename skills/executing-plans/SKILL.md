---
name: executing-plans
description: Inline fallback for trivial tasks (config-only, no logic) — workflow-driven-development is the default
---

# Executing Plans

Inline fallback for trivial/config-only plans created by `claude-code-flow:writing-plans`, or harnesses without `Workflow`/subagents. Non-trivial work → `claude-code-flow:workflow-driven-development`.

Announce: “I'm using the executing-plans skill as a fallback to implement this trivial plan inline.”

## Use Only When

All true: config/docs/mechanical only; no new behavior/tests; no parallel subtasks/review loop; `Workflow` or subagents unavailable. Otherwise invoke workflow-driven-development.

## Process

Read plan once; check blockers/ambiguity/missing verification; create todos; execute steps in order; run stated verification; before done use `claude-code-flow:verification-before-completion`; for integration/cleanup use `claude-code-flow:finishing-a-development-branch`.

## Stop

Stop when plan has critical gaps, unclear instruction, missing dependency/tooling, repeated verification failure, or task stops being trivial. Do not guess through blockers or continue inline once orchestration is needed.

## Red Flags

Never use this to avoid workflow-driven development, implement on main/master without consent, skip verification, or continue after failed verification without diagnosing cause.
