---
name: write-plan
description: Create a concrete, test-first implementation plan from an approved design or requirements.
---

# Write Plan

Use the `writing-plans` skill to produce a task-by-task implementation plan.

## Arguments

```
/write-plan <spec path or requirements>
```

## Process

1. Use `using-claude-code-flow`.
2. Read the referenced spec or requirements.
3. Use `writing-plans`.
4. Map files to responsibilities.
5. Create small tasks with failing-test, implementation, verification, and review steps.
6. Save the plan to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md` for substantial work.

## Output

- Plan path.
- Task count.
- Main verification commands.
- Recommended execution mode: subagent-driven or inline.
