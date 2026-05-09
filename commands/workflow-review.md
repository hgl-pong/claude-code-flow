---
name: workflow-review
description: Start the review pipeline — sentinel reviews recent changes or plan/design documents, produces a structured review report, and handles fix iterations.
---

# Workflow Review

Start the review pipeline for recent changes or plan/design documents.

## Process

1. **Identify review target**:
   - `--docs` flag: review plan/design documents (plan-brief.md, phase-context.md, DESIGN.md, etc.)
   - If no arguments: review uncommitted changes (git diff)
   - If arguments provided: review specified files or commit range

2. **Gather context**:
   - `--docs`: find documents in `.claude/flow/plans/` and `.claude/flow/designs/`
   - Otherwise: check for an approved plan file, read the changed files

3. **Invoke sentinel** with:
   - Task description
   - `--docs`: set `review_focus: document_quality`, paste full document content
   - Otherwise: plan/spec excerpt (paste the relevant requirements; do not only reference the path)
   - Files to review and diff summary
   - Focus areas (if specified)
   - Required output: `APPROVE`, `REQUEST CHANGES`, or `NEEDS DISCUSSION`, with exact `file:line` for every finding

4. **Handle review outcome**:
   - **APPROVE**: Report success
   - **REQUEST CHANGES**:
     - `--docs`: oracle revises the document, then re-review (max 3 rounds)
     - Otherwise: spawn forge to fix issues, then re-review (max 3 rounds)
   - **NEEDS DISCUSSION**: Present findings to user

## Usage

```
/workflow-review                              # Review uncommitted changes
/workflow-review src/auth/ src/api/           # Review specific directories
/workflow-review --docs                       # Review plan/design documents
/workflow-review --focus security             # Review with security focus
/workflow-review --plan docs/auth-plan.md     # Review against specific plan
```

## Max Review Rounds

If after 3 review rounds there are still issues, escalate to the user for a decision.
