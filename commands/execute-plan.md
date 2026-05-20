---
name: execute-plan
description: Execute an approved plan through TDD, review, and acceptance gates.
---

# Execute Plan

Execute a saved implementation plan using the `dev-orchestrator` pipeline.

## Arguments

```
/execute-plan <plan path>
```

## Process

1. Treat `/execute-plan` as the selected route; do not invoke `using-claude-code-flow` again unless no route context exists.
2. Use `executing-plans` to load, sanity-check, and sequence the approved plan. It owns plan interpretation.
3. Use `dev-orchestrator` for agent scheduling, context envelopes, verification, review, and acceptance. It owns pipeline execution.
4. Set mode and phase before dispatch:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode standard
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
   ```
5. Follow `skills/dev-orchestrator/references/pipeline-operations.md` for gate order and completion handling; do not restate or fork that checklist in this command.

## Source of Truth

- Plan execution loop: `skills/executing-plans/SKILL.md`
- Pipeline scheduling and acceptance: `skills/dev-orchestrator/SKILL.md`
- Gate checklist and completion handling: `skills/dev-orchestrator/references/pipeline-operations.md`

## Output

- Completed tasks.
- Files changed.
- Review and acceptance results.
- Verification commands and results.
