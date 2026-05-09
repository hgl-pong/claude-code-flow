---
name: finish
description: Complete development work — verify tests, then handle merge, PR, or cleanup.
---

# Finish Branch

Complete the current development work: verify tests, then handle merge, PR, or cleanup.

## Arguments

```
/finish
```

## Process

1. Use `finishing-branch` skill.
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
