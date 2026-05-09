---
name: Testing Strategy
version: "2.1.0"
description: "Use when implementing any feature or bugfix, before writing implementation code"
---

# Testing Strategy

## Iron Law

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

For behavior changes, write or identify a failing test before production code. Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

If code was already written as exploration, treat it as a spike: keep the learning, discard the code, start fresh from the test.

**Violating the letter of this rule is violating the spirit of this rule.**

## TDD: Red-Green-Refactor

1. **RED** — Write one minimal failing test showing desired behavior
2. **Verify RED** — Run it. Confirm it fails for the right reason (feature missing, not typo)
3. **GREEN** — Write the simplest code to pass
4. **Verify GREEN** — Run it. Confirm pass + no regressions
5. **REFACTOR** — Clean up while keeping tests green. No new behavior.

Required evidence:
- RED command and expected failure
- GREEN command and passing result
- Broader regression command before completion

Allowed exceptions, with user-visible note:
- Documentation-only edits
- Pure configuration changes that cannot be reasonably tested
- Throwaway prototypes
- Generated files where the generator is the tested surface

## Red Flags — STOP

- Code before test
- Test passes immediately (tests existing behavior, not new requirement)
- "I'll write tests after"
- "This is too simple for TDD"
- Can't explain why the test failed

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Manual is ad-hoc. No record, can't re-run. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD is faster than debugging. |

## Reference

For test patterns, anti-patterns, test doubles, organization, and coverage guidance see `test-patterns.md` in this directory.
