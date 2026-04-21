---
name: build-check
description: Standalone build check — verify the project builds, check for dependency issues, and run CI locally.
---

# Build Check

Verify the project builds correctly and check for common build issues.

## Arguments

- **Target** (optional): Specific build target or configuration
- **Mode** (optional): `build`, `test`, `lint`, or `all` (default: `all`)

## Process

1. Read build configuration files (package.json, CMakeLists.txt, Makefile, pyproject.toml, etc.)
2. Invoke anvil to:
   - Check build configuration for common issues
   - Run the build
   - Run tests (if requested)
   - Check dependency health (outdated, vulnerable)
3. Report results

## Usage

```
/build-check                                 # Full check: build + test + lint
/build-check --mode build                    # Build only
/build-check --mode test                     # Tests only
/build-check --mode lint                     # Lint only
/build-check src/api/                        # Check specific target
```

## Output

- Build result (success/failure with errors)
- Test results (if requested)
- Dependency issues (outdated, vulnerable)
- Suggestions for improvement
