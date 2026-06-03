# Code Quality Reviewer Prompt (Workflow Mode)

Use this template when constructing the code quality reviewer prompt for workflow-driven development.

**Purpose:** Verify the implementation is well-built — clean, tested, maintainable. Only dispatch after spec compliance review passes.

```
Task tool (general-purpose):
  description: "Review code quality: {{TASK_SUMMARY}}"
  prompt: |
    Review the implementation for code quality.

    ## Context

    Task: {{TASK_SUMMARY}}
    Commit: {{COMMIT_SHA}}
    Files: {{FILES_MODIFIED}}

    ## Instructions

    Read the actual code in the changed files. Evaluate:

    Cleanliness:
    - Are names clear and accurate (describe WHAT, not HOW)?
    - Is there dead code, duplicate logic, or unnecessary abstraction?
    - Are there magic numbers that should be named constants?

    Correctness:
    - Do tests verify real behavior (not just mock behavior)?
    - Are edge cases and error states handled?
    - Is there error handling for impossible scenarios (over-engineering)?

    Maintainability:
    - Does each file have one clear responsibility?
    - Are units independently testable?
    - Does the implementation follow the plan's file structure?
    - Did this change create files that are already large, or significantly grow existing files?

    Discipline:
    - No overbuilding (YAGNI) — nothing beyond what was requested
    - No orphaned imports or unused variables introduced by this change
    - Follows existing project conventions
    - No commented-out code or TODO markers left behind

    Do NOT flag pre-existing issues in files this task touched.
    Focus on what this change contributed. Pre-existing file size or
    code quality issues are not this implementer's responsibility.

    ## Structured Output

    {
      "passed": true | false,
      "issues": [
        {
          "severity": "Critical" | "Important" | "Minor",
          "file": "path/to/file.ts",
          "line": 42,
          "description": "what's wrong"
        }
      ],
      "summary": "strengths and overall assessment"
    }

    Only mark as Critical if the issue would cause a bug, break the build,
    or violate a core requirement. Important is for maintainability problems
    that should be addressed. Minor is for style nits.
```
