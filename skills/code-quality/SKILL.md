---
name: Code Quality
version: "1.0.0"
description: This skill should be used when the user asks about "code quality", "best practices", "clean code", "code smells", "refactoring", "design patterns", "SOLID principles", or any topic related to writing maintainable, well-structured code. Also triggers when reviewing code for quality issues.
---

# Code Quality Standards

Guidelines for writing clean, maintainable, production-quality code.

## Core Principles

### SOLID
- **Single Responsibility**: Each function/class does one thing
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes must be substitutable for base types
- **Interface Segregation**: Prefer small, focused interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

### DRY (Don't Repeat Yourself)
- Extract shared logic into functions/modules
- Three occurrences of similar code warrants extraction
- Balance DRY with clarity — sometimes duplication is clearer than abstraction

### KISS (Keep It Simple)
- Choose the simplest solution that works
- Avoid premature optimization
- Prefer readability over cleverness

## Code Structure

### Functions
- Small and focused — one level of abstraction per function
- Descriptive names that explain intent
- Max 3-4 parameters; use objects for more
- Return early for guard clauses
- No side effects in pure functions

### Error Handling
- Handle errors at the appropriate level
- Use custom error types for domain errors
- Don't swallow errors silently
- Validate input at system boundaries
- Distinguish between programmer errors (assert/throw) and recoverable errors (return error)

### Naming
- Use intention-revealing names
- Avoid abbreviations (unless universally known: URL, HTTP, ID)
- Booleans: `is`, `has`, `can`, `should` prefix
- Functions: verb phrases (`getUserById`, `calculateTotal`)
- Classes: nouns (`UserService`, `PaymentProcessor`)

## Common Code Smells

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

## Refactoring Patterns

- **Extract Method**: Turn a code block into a function
- **Extract Class**: Split a class with too many responsibilities
- **Introduce Parameter Object**: Group related parameters
- **Replace Conditional with Polymorphism**: Strategy pattern
- **Replace Magic Number with Constant**: Named constants
- **Move Method**: Move to the class that uses the data most

## When to Apply

Trigger this skill when:
- Writing new code that should follow quality standards
- Reviewing code for quality issues
- Deciding whether to refactor
- Choosing between design patterns
