# Fix Prompt (Workflow Mode)

Use this template when constructing the fix prompt for workflow-driven development review loops.

**Purpose:** Fix specific review issues without making other changes.

```
Task tool (general-purpose):
  description: "Fix review issues"
  prompt: |
    Fix the following review issues in the implementation.

    ## Issues to Fix

    {{ISSUES}}

    ## Files to Modify

    {{FILES_MODIFIED}}

    ## Instructions

    1. Read each file listed above
    2. Fix every issue described in the issues list
    3. Do NOT make changes beyond fixing these specific issues
    4. Do NOT refactor, restructure, or "improve" unrelated code
    5. Run the tests to verify nothing broke
    6. Commit with: `fix(review): address review findings`

    ## Structured Output

    {
      "status": "DONE" | "DONE_WITH_CONCERNS" | "BLOCKED",
      "summary": "what you fixed",
      "files_modified": ["file1.ts"],
      "test_results": "test command and output",
      "commit_sha": "def5678",
      "concerns": [],
      "blocker_detail": ""
    }
```
