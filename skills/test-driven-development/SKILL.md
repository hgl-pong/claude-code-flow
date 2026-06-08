---
name: test-driven-development
description: Use when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

Write test first. Watch it fail. Write minimal code to pass.

**Core principle:** if you didn't watch the test fail, you don't know it tests the right thing. Violating the letter is violating the spirit.

## Iron Law

`NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`

Write the test first, before code. NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

Code before test? Delete it. Start over. Don't keep as reference, adapt it, or look at it. Delete means delete. Implement fresh from tests.

## Use

Always for features, bugfixes, refactors, behavior changes. Exceptions only with human approval: throwaway prototypes, generated code, config files.

## Cycle

1. **RED:** write one minimal behavior test with clear name; prefer real code, mocks only if unavoidable.
2. **Verify RED:** run targeted test. It must fail for the expected missing behavior, not typo/setup. Passing immediately means wrong test.
3. **GREEN:** write minimal code: the simplest, just enough code that passes. No extra features, no unrelated cleanup.
4. **Verify GREEN:** targeted test + relevant suite pass; output clean.
5. **REFACTOR:** only while green; remove duplication, improve names, keep behavior unchanged.
6. Repeat for next behavior.

## Good Test Shape

```ts
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const op = async () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  await expect(retryOperation(op)).resolves.toBe('success');
  expect(attempts).toBe(3);
});
```

Tests one behavior, names intent, proves real behavior.

## Why Order Matters

Tests-after pass immediately → prove nothing. They answer “what does this implementation do?” not “what should it do?” They inherit your blind spots. Test-first proves the test catches absence of required behavior.

Manual testing is not a substitute: no record, not repeatable, misses edge cases under pressure.

Sunk cost is not a reason to keep untrusted code. Keeping code you can't test-first is technical debt.

## Rationalizations

| Excuse | Reality |
|---|---|
| Too simple | Simple code breaks; test takes seconds. |
| I'll test after | Immediate pass proves nothing. |
| Manual tested | Ad hoc, not repeatable. |
| Keep as reference | You'll adapt it. Delete. |
| Need to explore | Fine; throw exploration away, then TDD. |
| Test is hard | API/design is unclear; simplify. |
| Existing code lacks tests | Improve it with a focused test. |
| TDD is dogmatic | Debugging later is slower. |

## Red Flags — Start Over

Code before test; test after implementation; test passes immediately; unclear failure reason; “just this once”; “spirit not ritual”; “already spent hours”; “this is different”; adapting existing code.

All → delete production code and restart with a failing test.

## Completion Checklist

- [ ] Every new behavior/function has a test.
- [ ] Watched each test fail first for expected reason.
- [ ] Minimal code made it pass.
- [ ] Relevant/full tests pass cleanly.
- [ ] Edge/error cases covered.
- [ ] Real code used; mocks only when unavoidable.

Can't check all? You skipped TDD.

## When Stuck

| Problem | Fix |
|---|---|
| Don't know how to test | Write wished-for API/assertion first; ask if needed. |
| Test too complex | Simplify interface. |
| Must mock everything | Code too coupled; inject deps. |
| Setup huge | Extract helpers or simplify design. |

Bug found? First write failing repro. Never fix bugs without a test.

For test utilities/mocks, read `testing-anti-patterns.md` only when needed.
