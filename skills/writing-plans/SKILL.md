---
name: Writing Plans
version: "2.0.0"
description: "Use when you have an approved spec or requirements for a multi-step task, before touching code"
---

# Writing Plans

## Iron Law

**NO PLACEHOLDERS. NO VAGUE INSTRUCTIONS. EVERY TASK STANDS ALONE.**

A plan is written for a fresh agent with zero project context and zero ability to "figure it out." If a task cannot be executed by reading it alone, the plan is incomplete.

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The developer can figure it out" | If they could, they wouldn't need a plan. Be explicit. |
| "Similar to the previous task" | Similar is not identical. Repeat the details. |
| "I'll add TODOs for the tricky parts" | TODOs in a plan mean the plan is not done. |
| "The file path is obvious from context" | Context is what the plan creates. Write every path explicitly. |

## Red Flags — STOP

- "They'll know what I mean"
- "I'll skip the test command, it's standard"
- "I'll just reference the design doc"
- "The exact file doesn't matter at this stage"

## Process

1. Read the approved spec or requirements.
2. Map files to responsibilities — design units with clear boundaries and well-defined interfaces.
3. Split work into small test-first tasks (each step is 2-5 minutes).
4. Add exact commands and expected results. No "TBD", "TODO", "implement later".
5. Run the self-review checklist before handoff.

## Bite-Sized Task Granularity

Each step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

## Reference

For plan location, required header, task shape, agent assignment, quality bar, self-review, and handoff details see `plan-quality-guide.md` in this directory.

Every task must be convertible into a context envelope for the orchestrator: goal, exact task, working directory, completed dependencies, file scope, test command, acceptance criteria, relevant excerpts, constraints, and out-of-scope boundaries. The source of truth is the approved plan/spec plus `<output_dir>/phase-context.md`; do not rely on chat history.
