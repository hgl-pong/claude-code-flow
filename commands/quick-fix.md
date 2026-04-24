---
name: quick-fix
description: Quick fix mode — skip research and design, directly analyze and implement. For bug fixes, config changes, and single-file edits.
---

# Quick Fix

Streamlined workflow for small tasks. Skips research, design, and plan approval.

## Process

1. Set workflow mode to quick:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode quick
   ```

2. **Analyze**: Read the relevant code, identify the issue or change needed

3. **Implement**: Directly invoke forge with a focused prompt:
   ```
   Agent({
     name: "fix",
     subagent_type: "claude-code-flow:forge",
     model: "sonnet",
     prompt: "Fix: [specific issue]. File: [path]. Context: [relevant code]."
   })
   ```

4. **Optional review**: If the change affects critical paths or the user wants verification:
   ```
   Agent({
     name: "reviewer",
     subagent_type: "claude-code-flow:sentinel",
     model: "sonnet",
     prompt: "Review the change in [files]. Focus: correctness, no regressions."
   })
   ```

5. **Report**: Summarize what was changed and any caveats

## When to Use

- Bug fixes in a single file or small scope
- Configuration changes
- Typo/error corrections
- Small refactors (rename, extract function)
- Adding a missing import or dependency

## When NOT to Use

- New features spanning multiple files
- Architectural changes
- Tasks requiring external research
- Anything that needs a plan review

## Usage

```
/quick-fix Fix the null pointer in auth middleware
/quick-fix Update the API base URL in config
/quick-fix Add missing error handling to the database connection
```
