---
name: Systematic Debugging
version: "1.0.0"
description: Use when fixing bugs, test failures, crashes, flaky behavior, performance regressions, or any issue where the root cause is not already proven.
---

# Systematic Debugging

Debug from evidence. Do not patch symptoms until the root cause is proven.

## Process

1. **Capture the failure**
   - Reproduce the issue with the smallest command or scenario.
   - Save the exact error, logs, input, and environment assumptions.

2. **Localize**
   - Identify where the expected behavior first diverges from actual behavior.
   - Add temporary logging or assertions only as needed.
   - Inspect recent changes if they plausibly touched the failing path.

3. **Prove the cause**
   - Form one hypothesis at a time.
   - Run a check that would falsify it.
   - Do not stack speculative fixes.

4. **Fix with TDD**
   - Write a failing regression test that captures the bug.
   - Watch it fail for the right reason.
   - Implement the smallest fix.
   - Watch the test pass.

5. **Add defense in depth**
   - If the bug crossed a boundary, add validation or clearer errors at that boundary.
   - If the bug was caused by ambiguous ownership, document or refactor the boundary.

## Red Flags

- Fixing before reproducing.
- Assuming the cause from the error message alone.
- Changing multiple unrelated things in one attempt.
- Calling a flaky sleep a synchronization fix.
- Reporting success without rerunning the failing scenario.

## Completion Evidence

Report:

- Reproduction command or scenario.
- Root cause.
- Regression test added.
- Verification command and result.
