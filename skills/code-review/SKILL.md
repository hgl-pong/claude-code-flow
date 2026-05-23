---
name: Code Review
version: "1.0.0"
description: "Review code for correctness bugs, quality issues, risky refactors, SOLID/design smells, and review feedback."
when_to_use: "Trigger on 'review this code', 'code review', 'PR review', 'check my diff', 'code quality', 'review feedback'."
argument-hint: "<file, code area, or review feedback>"
---

# Code Review

Two sides of code review: **performing** reviews (quality evaluation) and **receiving** reviews (response discipline).

## Part 1: Performing Reviews

### Quality Standards

**EVERY CHANGE MUST LEAVE THE CODE CLEANER THAN YOU FOUND IT.**

#### Core Principles

- **SOLID**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY**: Extract shared logic. Three occurrences warrants extraction. Balance with clarity.
- **KISS**: Simplest solution that works. Prefer readability over cleverness.

#### Code Structure

- Small, focused functions — one level of abstraction per function
- Descriptive names that explain intent
- Max 3-4 parameters; use objects for more
- Return early for guard clauses
- No side effects in pure functions

#### Common Code Smells

| Smell | Fix |
|-------|-----|
| Long function | Extract sub-functions |
| Deep nesting | Early returns, guard clauses |
| God class | Extract responsibilities |
| Magic numbers | Named constants |
| Feature envy | Move method to data class |
| Primitive obsession | Value objects, types |
| Dead code | Delete it |
| Comments explaining "what" | Better naming |

#### Refactoring Patterns

- **Extract Method**: Turn a code block into a function
- **Extract Class**: Split a class with too many responsibilities
- **Introduce Parameter Object**: Group related parameters
- **Replace Conditional with Polymorphism**: Strategy pattern
- **Move Method**: Move to the class that uses the data most

#### Error Handling

- Handle errors at the appropriate level
- Use custom error types for domain errors
- Don't swallow errors silently
- Validate input at system boundaries
- Distinguish programmer errors (assert/throw) from recoverable errors (return error)

#### Naming

- Use intention-revealing names
- Booleans: `is`, `has`, `can`, `should` prefix
- Functions: verb phrases (`getUserById`, `calculateTotal`)
- Classes: nouns (`UserService`, `PaymentProcessor`)

## Part 2: Receiving Reviews

### Core Principle

**Verify before implementing. Ask before assuming. Technical correctness over social comfort.**

### Response Pattern

```
WHEN receiving code review feedback:

1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

### Forbidden Responses

**NEVER:**
- "You're absolutely right!" (performative)
- "Great point!" / "Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

### Handling Unclear Feedback

```
IF any item is unclear:
  STOP — do not implement anything yet
  ASK for clarification on unclear items

WHY: Items may be related. Partial understanding = wrong implementation.
```

### Source-Specific Handling

**From the user:**
- Trusted — implement after understanding
- Still ask if scope unclear
- No performative agreement

**From external reviewers:**
1. Check: Technically correct for THIS codebase?
2. Check: Breaks existing functionality?
3. Check: Reason for current implementation?
4. Check: Does reviewer understand full context?

If conflicts with user's prior decisions → stop and discuss first.

### YAGNI Check

```
IF reviewer suggests "implementing properly":
  grep codebase for actual usage

  IF unused: "This endpoint isn't called. Remove it (YAGNI)?"
  IF used: Then implement properly
```

### Implementation Order

For multi-item feedback:
1. Clarify anything unclear FIRST
2. Blocking issues (breaks, security)
3. Simple fixes (typos, imports)
4. Complex fixes (refactoring, logic)
5. Test each fix individually
6. Verify no regressions

### When to Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Conflicts with user's architectural decisions

**How:** Technical reasoning, not defensiveness. Ask specific questions. Reference working tests/code.

### Correcting Your Own Pushback

```
GOOD: "Verified — you're correct. My initial understanding was wrong because [reason]. Fixing."
BAD: Long apology
BAD: Defending why you pushed back
```

## Red Flags — STOP

- "This is good enough for now"
- "Nobody will look at this code anyway"
- "I'll add a comment to explain the hack"
- "It works, ship it"
- Implementing review feedback without verifying it's correct
- Performative agreement before technical evaluation
