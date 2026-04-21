---
name: workflow-review
description: Start the review pipeline — sentinel reviews recent changes against the plan, produces a structured review report, and handles fix iterations.
---

# Workflow Review

Start the code review pipeline for recent or specified changes.

## Process

1. **Identify changes to review**:
   - If no arguments: review uncommitted changes (git diff)
   - If arguments provided: review specified files or commit range

2. **Gather context**:
   - Check for an approved plan file in the project
   - Read the changed files

3. **Invoke sentinel** with:
   - Task description
   - Plan reference (if available)
   - Files to review
   - Focus areas (if specified)

4. **Handle review outcome**:
   - **APPROVE**: Report success
   - **REQUEST CHANGES**: Spawn forge to fix issues, then re-review (max 3 rounds)
   - **NEEDS DISCUSSION**: Present findings to user

## Usage

```
/workflow-review                              # Review uncommitted changes
/workflow-review src/auth/ src/api/           # Review specific directories
/workflow-review --focus security             # Review with security focus
/workflow-review --plan docs/auth-plan.md     # Review against specific plan
```

## Max Review Rounds

If after 3 review rounds there are still issues, escalate to the user for a decision.
