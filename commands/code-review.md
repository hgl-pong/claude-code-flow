---
name: code-review
description: Standalone code review — review specific files, functions, or recent changes without the full pipeline.
---

# Code Review

Perform a focused code review on specified targets, or handle external review feedback.

## Arguments

- **Target**: File path, directory, or `--diff` for uncommitted changes
- **Focus** (optional): `security`, `performance`, `correctness`, `architecture`, or custom description
- **--receive**: Switch to receiving mode — handle external code review feedback using `receiving-code-review` skill

## Process

### Reviewing Code (default)

1. Identify files to review from arguments or git diff
2. Read the target files or diff enough to give sentinel concrete context
3. Invoke sentinel with the target files, relevant diff excerpts, focus area, and any available requirements
4. Present the review report to the user

### Receiving Review Feedback (--receive)

1. Use `receiving-code-review` skill
2. READ all feedback completely before reacting
3. VERIFY each suggestion against codebase reality
4. EVALUATE technical correctness before implementing
5. IMPLEMENT one item at a time with testing

## Usage

```
/code-review src/auth/login.ts                 # Review a file
/code-review src/api/ --focus security         # Review directory with security focus
/code-review --diff                            # Review uncommitted changes
/code-review --diff --focus performance        # Review changes for performance
/code-review --receive                         # Handle external review feedback
```

## Output

### Review Report (default)

Structured review report with:
- Critical issues (must fix)
- Warnings (should fix)
- Suggestions (nice to have)
- Architecture compliance check
- Exact `file:line` evidence for every finding

### Received Feedback (--receive)

- Verified understanding of each feedback item
- Technical evaluation of each suggestion
- Implemented fixes with test evidence
- Pushback on incorrect suggestions with reasoning
