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
3. Read the plan and extract tasks, dependencies, file scopes, test commands, and acceptance criteria.
4. Set mode and phase:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode standard
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
   ```
5. For each task or non-conflicting task batch:
   - Apply `testing-strategy` before production code.
   - Build a self-contained context envelope from the plan. Paste the relevant plan excerpts directly; do not ask subagents to "read the plan."
   - Dispatch implementation to `forge`, testing/acceptance to `prism`, review to `sentinel`.
   - Run focused verification.
   - Run `sentinel` for spec and quality review.
   - Run `prism` for acceptance when the task affects behavior.
6. Use `verification-before-completion` before reporting done.

## Dispatch Prompt Requirements

Every implementation dispatch must include:
- Goal, task, working directory, completed dependencies, exact file scope.
- Exact test command and acceptance criteria.
- Relevant plan/design/code excerpts needed to work without hidden context.
- Explicit out-of-scope files or behaviors.
- Required `FILES_MODIFIED` declaration and verification output.

## Output

- Completed tasks.
- Files changed.
- Review and acceptance results.
- Verification commands and results.
