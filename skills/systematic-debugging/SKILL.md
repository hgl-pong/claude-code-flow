---
name: systematic-debugging
description: "Debug bugs, test failures, crashes, build failures, regressions, performance issues, and unexpected behavior via root-cause analysis. Use when there is a symptom to diagnose; skip feature planning or broad review."
---

# Systematic Debugging

Find root cause before fixing.

## Iron Law

No fix without a reproduced symptom and a root-cause hypothesis supported by evidence.

## Workflow

1. Capture the exact symptom, expected behavior, and recent changes.
2. Reproduce with the narrowest command/test/action that still exercises the symptom.
3. Localize the failing boundary using logs, tests, traces, or code paths.
4. Form and test a root-cause hypothesis.
5. Add or update a regression test when possible.
6. Apply a scoped fix only after the failing boundary is isolated.
7. Re-run the failing check and nearby regression checks.

## Output

- Symptom
- Reproduction
- Root cause
- Fix
- Verification evidence

## References

- `phases.md` - full debugging phases.
