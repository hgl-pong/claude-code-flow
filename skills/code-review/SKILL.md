---
name: code-review
description: "Review code for correctness bugs, quality issues, risky refactors, SOLID/design smells, and review feedback. Use when the user asks for code review, PR review, diff checking, review feedback triage, or quality assessment; skip direct implementation/test-only requests."
---

# Code Review

Review for defects and actionable risk, not stylistic churn.

## Rules

- Inspect spec compliance before code quality.
- Prioritize correctness, security, data loss, regressions, and maintainability risks.
- Report only high-confidence findings.
- Include `file:line`, impact, and minimal fix direction.
- If asked to receive review feedback, classify each comment as accept / clarify / reject with rationale.

## Workflow

1. Determine review target: current diff, files, PR, or feedback list.
2. Read relevant spec/requirements if present.
3. Stage 1: check whether implementation satisfies requested behavior.
4. Stage 2: check quality, security, tests, and edge cases.
5. Summarize findings by severity; say "No findings" if clean.

## Output

- Findings by severity
- Evidence inspected
- Tested / not tested
- Follow-up questions only if blocking

