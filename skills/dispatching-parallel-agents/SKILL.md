---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

# Dispatching Parallel Agents

Delegate one isolated agent per independent problem domain. Give only needed context; preserve coordinator context.

## Use When

- 2+ independent failures/subsystems/tasks.
- Each can be understood without others.
- No shared files/state/resources.
- Parallel work won't conflict.

Do not use when failures are related, full-system context is needed, or agents would edit/use the same state.

## Pattern

1. **Group domains** by root area: test file, subsystem, bug class.
2. **Create focused prompts** with scope, goal, constraints, expected output.
3. **Dispatch concurrently**.
4. **Integrate**: read summaries, inspect changes, check conflicts, run full suite, spot-check.

## Prompt Contract

Include:

- Specific scope: file/subsystem/test names.
- Concrete failures/errors.
- Goal: what success means.
- Constraints: files allowed/forbidden, no broad refactor, no timeout bumps unless justified.
- Expected return: root cause, changes, verification run, concerns.

Example:

```text
Fix failures in src/agents/agent-tool-abort.test.ts:
1. <test name> — <error>
2. <test name> — <error>

Find root cause. Do not just increase timeouts. Return summary, files changed, verification.
```

## Common Mistakes

| Mistake | Fix |
|---|---|
| “Fix all tests” | One agent per file/domain. |
| Missing context | Paste errors/test names. |
| No constraints | State allowed changes. |
| Vague output | Require root cause + verification. |
| Related failures split | Investigate together first. |

## Verification

After agents return: verify diffs, conflicts, full suite, and systematic errors. Agent success reports are not evidence.
