# Review Workflow Reference

Shared source of truth for review command boundaries, sentinel dispatch inputs, and review outcome handling.

## Scope

| Surface | Use it for | Owns |
|---|---|---|
| `/code-review` | Standalone review of explicit files, directories, functions, or a git diff | Target selection outside the active pipeline; optional external feedback handling |
| `/workflow-review` | Workflow-gated review of plan/design documents, workflow-tracked changes, or approved-plan implementation | Review gate execution, fix loops, and handoff back to acceptance |
| `agents/sentinel.md` | Reviewer behavior | Read-only review, exact evidence requirements, stage ordering, document review mode |
| `pipeline-operations.md` | Pipeline scheduling | Gate order, mode behavior, acceptance handoff |

## Command Boundaries

- `/code-review` is the ad hoc entry point. Use it when the user wants a focused review outside the plan -> implementation -> review -> acceptance pipeline.
- `/workflow-review` is the pipeline gate entry point. Use it when review is tied to an approved plan, workflow state, workflow-tracked changes, or plan/design documents.
- Default review mode is read-only. Do not modify files while producing a review report.
- `/code-review --receive` is feedback-response mode, not review-report mode. It uses `skills/code-review/SKILL.md` (Part 2: Receiving Reviews) and may implement verified feedback items with tests.
- Do not copy sentinel's full review checklist into slash commands. Commands gather context and route; sentinel evaluates.

## Target Selection

| Command | Target rules |
|---|---|
| `/code-review <targets>` | Review the explicit files, directories, functions, or ranges supplied by the user |
| `/code-review --diff` | Review uncommitted changes from git diff |
| `/code-review --receive` | Treat user-provided or external reviewer feedback as the primary input |
| `/workflow-review --docs` | Review plan/design documents such as `plan-brief.md`, `phase-context.md`, `DESIGN.md`, and `*-design.md` |
| `/workflow-review` with no args | Prefer workflow-tracked changes; fall back to git diff when workflow state is absent |
| `/workflow-review <targets>` | Review specified files, directories, documents, or commit ranges as a workflow gate |
| `/workflow-review --plan <path>` | Use the specified plan as the spec excerpt for implementation review |

## Sentinel Dispatch Contract

Every sentinel dispatch must include:

- task description or user request
- review target paths and relevant diff/content excerpts
- pasted plan/spec requirements when reviewing implementation; do not only reference a path
- `review_focus` when narrowing scope: `spec_compliance`, `code_quality`, or `document_quality`
- focus area from user flags, if any
- required outcome labels: `APPROVE`, `REQUEST CHANGES`, or `NEEDS DISCUSSION`
- requirement that every finding cites exact `file:line` evidence, or `file > section` evidence for documents

## Multi-Round Review Loop

Non-trivial workflow changes require a review loop, not a one-shot review. Each round has a bounded input, a sentinel report, a fix decision, fresh verification, and re-review.

1. Dispatch sentinel for the current review focus.
2. If `APPROVE`, continue to the next review stage or acceptance gate.
3. If `REQUEST CHANGES`, convert each accepted finding into a scoped fix task with exact file paths and verification.
4. Dispatch forge for fixes; do not let sentinel modify files.
5. Dispatch or run prism verification for the fixed scope.
6. Dispatch a fresh sentinel re-review with the original spec, prior findings, changed files, and fresh evidence.
7. Stop only on `APPROVE`, `NEEDS DISCUSSION`, or the review round limit.

## Outcome Handling

- `APPROVE`: report success. In workflow mode, continue to the next gate or acceptance handoff.
- `REQUEST CHANGES`: run the multi-round fix loop, then re-review. For document review, oracle revises documents. For implementation review, forge fixes code.
- `NEEDS DISCUSSION`: stop the loop and present the decision point to the user.
- Stop after 3 review rounds and escalate to the user with remaining findings and options.

## Output Contract

Review reports should lead with findings, then open questions, then a brief summary. Include:

- assessment: `APPROVE`, `REQUEST CHANGES`, or `NEEDS DISCUSSION`
- risk level
- review focus
- files or documents reviewed
- exact evidence for each finding

For external feedback received through `/code-review --receive`, report verified understanding, implemented items with test evidence, and technical pushback for rejected suggestions.

## Review Reception Gate

Verify before implementing review feedback. Restate or clarify unclear feedback, check it against codebase reality, then either implement with tests or give technical pushback. External feedback is a suggestion to evaluate, not an order to follow.

For pipeline review, the spec compliance reviewer must approve before code quality review starts. If spec compliance requests changes, fix and re-review spec compliance before any quality review. Quality findings then follow the same fix-and-re-review loop.

## One Feedback Item at a Time

When implementing review feedback, handle one feedback item at a time unless items are inseparable. For each item: verify it against codebase reality, decide accept/reject, implement accepted changes, run focused verification, then continue. Use technical pushback for incorrect, unused, or scope-expanding suggestions.
