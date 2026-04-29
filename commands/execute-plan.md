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

1. Use `using-claude-code-flow`.
2. Use `dev-orchestrator`.
3. Read the plan once and extract tasks.
4. Set mode and phase:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode standard
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
   ```
5. For each task:
   - Apply `testing-strategy` before production code.
   - Dispatch implementation to the right agent (`forge`, `weaver`, `prism`, `anvil`).
   - Run focused verification.
   - Run `sentinel` for spec and quality review.
   - Run `validator` for acceptance when the task affects behavior.
6. Use `verification-before-completion` before reporting done.

## Output

- Completed tasks.
- Files changed.
- Review and acceptance results.
- Verification commands and results.
