---
name: ultrawork
description: "Run ULI/Ultra Loop Iteration autonomous execution. Use for 'uli', legacy 'ulw'/'ultrawork', autonomous product iteration, or requests to proceed without approval gates."
---

# Ultrawork

Run ULI as the single autonomous execution mode. Legacy `ulw` and `ultrawork` activations are aliases for ULI.

## Workflow

1. Read `ULI.md`.
2. Initialize ULI state with `hooks/scripts/flow-state.py`.
3. Set autonomous mode and plan phase.
4. Create a task slug and write task artifacts under `.claude/flow/uli/<slug>/`.
5. Execute the full ULI loop until the product goal is complete or blocked by an external requirement.
6. Verify with fresh evidence.
7. Emit `<uli-done>` only after completion criteria are met.

## Rules

- No speculative scope expansion.
- Keep task-local artifacts under the ULI task directory.
- Respect security/destructive-action safety boundaries.
- If blocked, record the blocker and stop only with a clear reason.

## References

- `ULI.md` - autonomous iteration protocol.
