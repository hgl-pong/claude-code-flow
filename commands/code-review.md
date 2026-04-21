---
name: code-review
description: Standalone code review — review specific files, functions, or recent changes without the full pipeline.
---

# Code Review

Perform a focused code review on specified targets.

## Arguments

- **Target**: File path, directory, or `--diff` for uncommitted changes
- **Focus** (optional): `security`, `performance`, `correctness`, `architecture`, or custom description

## Process

1. Identify files to review from arguments or git diff
2. Invoke sentinel with the target files and focus area
3. Present the review report to the user

## Usage

```
/code-review src/auth/login.ts                 # Review a file
/code-review src/api/ --focus security         # Review directory with security focus
/code-review --diff                            # Review uncommitted changes
/code-review --diff --focus performance        # Review changes for performance
```

## Output

Structured review report with:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (nice to have)
- Architecture compliance check
