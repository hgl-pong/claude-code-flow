---
name: Testing Strategy
version: "3.0.0"
description: "Design test strategies and test plans. Trigger with 'how should we test', 'test strategy for', 'write tests for', 'test plan', 'what tests do we need', 'testing approach', or before implementing any feature or bugfix."
argument-hint: "<feature or component to test>"
---

# Testing Strategy

## Iron Law

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

For behavior changes, write or identify a failing test before production code. Write code before the test? Delete it. Start over.

Allowed exceptions, with user-visible note:
- Documentation-only edits
- Pure configuration changes that cannot be reasonably tested
- Throwaway prototypes
- Generated files where the generator is the tested surface

## Testing Pyramid

```
        /  E2E  \           Few, slow, high confidence
       / Integration \      Some, medium speed
      /    Unit Tests  \    Many, fast, focused
```

**Pyramid principle**: Most tests at the unit level (fast, isolated), fewer integration tests, fewest E2E tests (slow, brittle). Inverted pyramids are fragile and expensive to maintain.

## Strategy by Component Type

### API Endpoints
- **Unit**: Business logic, validation, transformation functions
- **Integration**: HTTP layer (request/response, status codes, headers)
- **Contract**: Consumer expectations (Pact, OpenAPI schema validation)

### Data Pipelines
- Input validation and schema conformance
- Transformation correctness (input → expected output)
- Idempotency tests (run twice, same result)
- Edge cases: empty input, oversized input, malformed data

### Frontend
- **Component tests**: Render, props, state changes
- **Interaction tests**: Click, type, submit, navigation
- **Visual regression**: Snapshot comparison (when applicable)
- **Accessibility**: ARIA, keyboard nav, contrast

### Infrastructure
- Smoke tests after deploy
- Health check endpoints
- Load/stress tests for critical paths
- Chaos engineering for resilience

### CLI Tools
- Argument parsing and flag combinations
- Exit codes for success/failure/usage errors
- Output format correctness (text, JSON, quiet mode)
- Edge cases: missing args, invalid input, piped stdin

### Libraries / Packages
- Public API contract tests (exported functions/classes)
- Edge case inputs (null, empty, wrong types)
- Backward compatibility for published APIs
- Type correctness (if typed language)

### Database / Auth
- Migration up/down idempotency
- Schema validation and constraint enforcement
- Auth flow: login, logout, token refresh, expired tokens
- Authorization: role-based access, permission boundaries

## What to Cover vs Skip

**Cover**: Business-critical paths, error handling, edge cases, security boundaries, data integrity, authorization checks, concurrent access.

**Skip**: Trivial getters/setters, framework boilerplate, one-off scripts, third-party library internals.

## TDD: Red-Green-Refactor

1. **RED** — Write one minimal failing test showing desired behavior
2. **Verify RED** — Run it. Confirm it fails for the right reason
3. **GREEN** — Write the simplest code to pass
4. **Verify GREEN** — Run it. Confirm pass + no regressions
5. **REFACTOR** — Clean up while keeping tests green. No new behavior.

Required evidence:
- RED command and expected failure
- GREEN command and passing result
- Broader regression command before completion

## Test Plan Output

```markdown
## Test Plan: [Feature/Component]

### Scope
[What is being tested and why]

### Test Matrix
| Area | Test Type | What to Verify | Priority |
|------|-----------|---------------|----------|
| [Area] | Unit | [Behavior] | P0/P1/P2 |

### Coverage Targets
| Layer | Target | Current |
|-------|--------|---------|
| Unit | [X]% | [X]% |
| Integration | [X]% | [X]% |
| E2E | [X] scenarios | [X] |

### Gaps Identified
- [Missing test coverage area]

### Test Commands
- Unit: `[command]`
- Integration: `[command]`
- E2E: `[command]`
```

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Manual is ad-hoc. No record, can't re-run. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD is faster than debugging. |

## Red Flags — STOP

- Code before test
- Test passes immediately (tests existing behavior, not new requirement)
- "I'll write tests after"
- "This is too simple for TDD"
- Can't explain why the test failed

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_query` to find execution flows and identify all code paths needing coverage
- Use `gitnexus_impact` to understand which functions callers depend on (higher risk → more tests)

If **~~browser** is connected:
- Run live E2E smoke tests against a running dev server
- Take screenshots to verify UI rendering after changes
- Automate click-through flows for acceptance testing

## Tips

1. **Start with the happy path** — Get the core flow green before testing edge cases
2. **Test behavior, not implementation** — Test what the code does, not how it does it
3. **One assertion per test concept** — Each test should verify one behavior

## Reference

For test patterns, anti-patterns, test doubles, organization, and coverage guidance see `test-patterns.md` in this directory.
