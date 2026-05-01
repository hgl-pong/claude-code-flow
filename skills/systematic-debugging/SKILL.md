---
name: Systematic Debugging
version: "1.0.0"
description: Use when fixing bugs, test failures, crashes, flaky behavior, performance regressions, or any issue where the root cause is not already proven.
---

# Systematic Debugging

## IRON LAW

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Reproduce the failure. Prove the cause. Then fix. Patching without understanding is how bugs multiply.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The bug is obvious" | Obvious bugs are often wrong bugs. Prove it. |
| "Just a typo, no need to reproduce" | Typos can mask deeper issues. Run the failing test. |
| "Same error as last time" | Same symptom does not mean same cause. Verify. |
| "I'll add a quick fix and see if it works" | Stacking unverified fixes makes debugging harder. One hypothesis at a time. |
| "The logs tell me exactly what's wrong" | Logs describe symptoms, not causes. Trace to the source. |

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
