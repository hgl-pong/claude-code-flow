---
name: finish
description: Complete development work — verify tests, then handle merge, PR, or cleanup.
allowed-tools:
  - Bash(rtk git status*)
  - Bash(rtk git diff*)
  - Bash(rtk python tests/run-tests.py*)
  - Bash(rtk git merge*)
  - Bash(rtk git branch*)
  - Bash(rtk git worktree*)
  - Bash(rtk gh pr create*)
---

# Finish Branch

Complete the current development work: verify tests, then handle merge, PR, or cleanup.

## Arguments

```
/finish
```

## Process

1. Use `dev-orchestrator` finish-branch phase (see `skills/dev-orchestrator/references/finish-branch.md`).
2. Verify tests pass.
3. Detect environment (worktree vs normal repo).
4. Present completion options to the user.
5. Execute the chosen option.

## Usage

```
/finish
```

## Output

- Test verification result
- Structured completion options
- Executed action (merge/PR/keep/discard)
