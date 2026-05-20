---
name: workflow-review
description: Start the review pipeline — sentinel reviews recent changes or plan/design documents, produces a structured review report, and handles fix iterations.
---

# Workflow Review

Start the review pipeline for recent changes or plan/design documents.

Use this command for workflow-gated review. For an ad hoc review of arbitrary files or a diff, prefer `/code-review`.

Use `skills/dev-orchestrator/references/review.md` as the source of truth for review target selection, sentinel dispatch inputs, output contract, and fix-loop outcome handling.

## Process

1. Follow the workflow-gated target rules in `skills/dev-orchestrator/references/review.md`.
2. Gather plan/design documents, workflow state, git diff, and pasted requirements needed for a self-contained sentinel dispatch.
3. Invoke sentinel with the review focus and evidence contract from the review reference.
4. Handle `APPROVE`, `REQUEST CHANGES`, and `NEEDS DISCUSSION` using the shared outcome rules.

Keep the review loop aligned with `skills/dev-orchestrator/references/pipeline-operations.md`; that reference owns the full review/acceptance gate behavior.

## Usage

```
/workflow-review                              # Review uncommitted changes
/workflow-review src/auth/ src/api/           # Review specific directories
/workflow-review --docs                       # Review plan/design documents
/workflow-review --focus security             # Review with security focus
/workflow-review --plan docs/auth-plan.md     # Review against specific plan
```

## Source of Truth

- Review command boundaries and outcome handling: `skills/dev-orchestrator/references/review.md`
- Review gate ordering: `skills/dev-orchestrator/references/pipeline-operations.md`
- Sentinel behavior: `agents/sentinel.md`
- Document review rules: `agents/sentinel.md` with `review_focus: document_quality`
