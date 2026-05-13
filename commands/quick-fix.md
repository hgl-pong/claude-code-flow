---
name: quick-fix
description: Quick fix mode — skip research and design, directly analyze and implement. For bug fixes, config changes, and single-file edits.
---

# Quick Fix

Streamlined workflow for small tasks. Skips research, design, and plan approval.

## Process

1. Treat `/quick-fix` as the selected route and classify whether this is truly quick. Do not invoke `using-claude-code-flow` again unless no route context exists.

2. If this is a bug with unknown cause, use `systematic-debugging` first.

3. Set workflow mode to quick:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode quick
   ```

4. **Analyze**: Read the relevant code, identify the issue or change needed

5. **Test first when behavior changes**: Use `testing-strategy` to write or identify the failing regression test before production edits.

6. **Choose agent**:
   - `forge` for all code implementation (backend + frontend).
   - `prism` for test-only work, builds, or acceptance checks.

7. **Implement**: Invoke the chosen agent with a complete context envelope. Do not use a one-line fix prompt.
   ```
   Agent({
     description: "quick fix: [specific issue]",
     subagent_type: "claude-code-flow:<agent>",
     model: "sonnet",
     prompt: "## Envelope\n- Goal: <user-visible outcome>\n- Your Task: <one concrete fix>\n- Working Directory: <cwd>\n- Completed Dependencies: N/A - quick fix\n- File Scope: <exact files allowed>\n- Test Command: `<focused verification command>`\n- Acceptance Criteria: <observable result>\n- Relevant Excerpts: <bug, stack trace, code snippets, or design note>\n- Constraints: keep change minimal; no unrelated refactors; follow repo style\n- Out of Scope: <files/features not to touch>\n\n## FILES_MODIFIED (required on completion)\nList ALL files created or modified.\n\n## Completion Schema\n- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED\n- Files modified:\n- Verification:\n- RED/GREEN evidence:\n- Concerns:"
   })
   ```

8. **Optional review**: If the change affects critical paths or the user wants verification:
   ```
   Agent({
     description: "quick fix review",
     subagent_type: "claude-code-flow:sentinel",
     model: "sonnet",
     prompt: "Review the change in <files>. First check the quick-fix acceptance criteria, then correctness/regression risk. Cite exact file:line for every finding."
   })
   ```

9. **Verify and report**: Use `verification-before-completion`; summarize what changed, what passed, and any caveats.

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
