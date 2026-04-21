---
name: write-tests
description: Standalone test writing — generate tests for specified modules, functions, or files.
---

# Write Tests

Generate tests for specified targets.

## Arguments

- **Target**: File path, directory, or module name to test
- **Type** (optional): `unit`, `integration`, `benchmark`, or `all` (default: `unit`)

## Process

1. Read the source code to understand what needs testing
2. Check existing tests to understand the project's test framework and conventions
3. Invoke prism with the target and test type
4. Run the tests to verify they pass
5. Report coverage gaps

## Usage

```
/write-tests src/auth/login.ts                 # Unit tests for a file
/write-tests src/api/ --type integration       # Integration tests for a directory
/write-tests src/utils/parser.ts --type all    # All test types
/write-tests src/db/ --type benchmark          # Performance benchmarks
```

## Output

- Test files created
- Test case count
- Test results (pass/fail)
- Coverage gaps identified
