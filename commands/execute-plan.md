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
2. Use `executing-plans` skill for the execution workflow.
3. Use `dev-orchestrator` for pipeline management.
4. Set mode and phase:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode standard
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
   ```
5. The skill handles: load plan, review, execute tasks with TDD, verify, report.

## Output

- Completed tasks.
- Files changed.
- Review and acceptance results.
- Verification commands and results.
