---
name: Testing Strategy
version: "1.0.0"
description: This skill should be used when the user asks about "testing", "write tests", "test strategy", "test coverage", "unit tests", "integration tests", "end-to-end tests", "mocking", "TDD", or any testing-related topic. Triggers when planning test approach, writing tests, or setting up test infrastructure.
---

# Testing Strategy

Guidelines for effective software testing across all test types.

## Test Pyramid

```
        /\
       /  \      E2E Tests (few, slow, high confidence)
      /----\
     /      \    Integration Tests (moderate count)
    /--------\
   /          \  Unit Tests (many, fast, focused)
  /____________\
```

- **Unit tests**: Test individual functions/classes in isolation. Should be the majority of tests.
- **Integration tests**: Test module interactions with real dependencies. Fewer than unit tests.
- **E2E tests**: Test complete user workflows. Fewest tests, highest maintenance cost.

## Unit Testing

### Principles
- Test behavior, not implementation
- Each test tests one thing
- Arrange-Act-Assert pattern
- Deterministic — no random failures
- Fast — aim for < 10ms per test

### Test Naming
```
test("UserRepository.findById returns null for non-existent user")
test("PaymentProcessor.charge throws InsufficientFundsError when balance too low")
test("EmailValidator.isValid returns true for valid email formats")
```

### What to Test
- Happy path (expected behavior)
- Edge cases (empty input, max values, boundary conditions)
- Error cases (invalid input, network failure, timeout)
- Business rule violations

## Integration Testing

### Principles
- Test real interactions between modules
- Use real databases, APIs, services (not mocks)
- Focus on contract verification
- Test error scenarios (connection failures, timeouts)

### Setup
- Use test databases (in-memory or containerized)
- Seed with known data
- Clean up after each test

## Test Organization

```
src/
  auth/
    auth.service.ts
    auth.service.test.ts      # Co-located tests
    auth.service.integration.test.ts
tests/
  e2e/
    auth-flow.test.ts          # E2E tests separate
  fixtures/
    users.json                 # Test data
    mock-responses/
```

## Test Doubles

| Type | When to Use |
|------|-------------|
| Stub | Return canned responses |
| Mock | Verify interactions (called with what args) |
| Spy | Record calls but use real behavior |
| Fake | In-memory implementation (e.g., in-memory DB) |

Prefer fakes over mocks when possible — they're simpler and more reliable.

## TDD (Test-Driven Development)

When writing new features:
1. **Red**: Write a failing test that describes the desired behavior
2. **Green**: Write the minimum code to make the test pass
3. **Refactor**: Improve the code while keeping tests green

TDD works best for:
- New modules with clear interfaces
- Bug fixes (write regression test first)
- Complex business logic

## Coverage

- Aim for high coverage on critical paths (auth, payments, data integrity)
- Don't chase 100% — diminishing returns
- Coverage without quality is meaningless
- Focus on branch coverage over line coverage

## When to Apply

Trigger this skill when:
- Planning test approach for a feature
- Writing tests for new or existing code
- Setting up test infrastructure
- Deciding between test types or frameworks
