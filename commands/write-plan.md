---
name: write-plan
description: Create a concrete, test-first implementation plan from approved requirements and persist it as structured workflow state.
---

# Write Plan

Use the `planning` skill (Phase 1: Write Plan) to produce a task-by-task implementation plan.

## Arguments

```
/write-plan <spec path or requirements>
```

## Process

1. Treat `/write-plan` as the selected route; the entry routing in `dev-orchestrator` has already classified this task.
2. Read the referenced spec or requirements.
3. Use `planning` (Phase 1: Write Plan).
4. Map files to responsibilities.
5. Create small tasks with failing-test, implementation, verification, and review steps.
6. Save the plan through `flow-state.py plan-init`, `plan-update`, `plan-add-task`, and `plan-approve`.
7. Export the approved brief to `.claude/flow/plans/<task-slug>/plan-brief.md` instead of writing a doc-first plan under `docs/`.

## Output

- Plan hash, `.claude/flow/plan-state.json`, and `.claude/flow/workflow-state.json`.
- Plan export brief path.
- Task count.
- Main verification commands.
- Recommended execution mode: subagent-driven or inline.
