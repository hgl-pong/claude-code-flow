---
name: testing-strategy
description: "Design test strategies, test plans, TDD coverage, regression tests, unit/integration/E2E checks, and verification scope. Use when asked how to test, what tests to write, test strategy/plan, TDD, coverage gaps, or regression protection."
---

# Testing Strategy

Choose the smallest test set that proves the behavior and catches likely regressions.

## Rules

- For behavior changes, write or specify the failing test first.
- Prefer lower-level tests unless integration boundaries are the risk.
- Include edge cases that matter to users or data integrity.
- Do not test implementation details unless they are the contract.

## Workflow

1. Name the behavior and risk to verify.
2. Pick test levels: unit, integration, E2E, manual, or static checks.
3. Identify files/fixtures/data needed.
4. Define RED/GREEN expectations.
5. List commands and expected evidence.
6. Note coverage gaps and why they are acceptable.

## Output

- Test scope
- Test levels and rationale
- Test cases
- Commands / expected results
- Gaps or skipped verification

## References

- `test-patterns.md` - patterns for choosing and writing tests.
