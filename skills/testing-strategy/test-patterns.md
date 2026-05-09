# Test Patterns Reference

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

- **Unit tests**: Test individual functions/classes in isolation. Should be the majority.
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

## Testing Anti-Patterns

- Tests that only assert mocks were called instead of observable behavior
- Snapshot updates without explaining the behavioral change
- Broad end-to-end tests where a fast unit or integration test would prove the same thing
- "Happy path only" coverage on validation, authorization, persistence, or money/data-loss paths
- Tests added after implementation that were never seen fail

## Coverage

- Aim for high coverage on critical paths (auth, payments, data integrity)
- Don't chase 100% — diminishing returns
- Coverage without quality is meaningless
- Focus on branch coverage over line coverage
