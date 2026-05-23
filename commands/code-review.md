---
name: code-review
description: Standalone code review — review specific files, functions, or recent changes without the full pipeline.
argument-hint: "<target|--diff> [--focus area] [--receive]"
allowed-tools:
  - Agent
  - Read
  - Grep
  - Glob
  - Bash(rtk git diff*)
  - Bash(rtk git status*)
---

# Code Review

Perform a focused code review on specified targets, or handle external review feedback.

Use this command for standalone review outside the active workflow pipeline. Use `/workflow-review` when review is a gate for an approved plan, workflow-tracked changes, or plan/design documents.

Use `skills/dev-orchestrator/references/review.md` as the source of truth for review command boundaries, target selection, sentinel dispatch inputs, and outcome handling.

## Arguments

- **Target**: File path, directory, or `--diff` for uncommitted changes
- **Focus** (optional): `security`, `performance`, `correctness`, `architecture`, or custom description
- **--receive**: Switch to receiving mode — handle external code review feedback using `code-review` skill

## Process

1. If the request is tied to an approved plan, workflow state, workflow-tracked changes, or plan/design documents, route to `/workflow-review`.
2. For default review mode, follow the standalone review rules in `skills/dev-orchestrator/references/review.md` and invoke sentinel with concrete targets, excerpts, focus, and any available requirements.
3. For `--receive`, use `skills/code-review/SKILL.md` (Part 2: Receiving Reviews); verify each feedback item against the codebase before implementing, then test each implemented item.
4. Present the review report or feedback-response summary using the reference output contract.

## Usage

```
/code-review src/auth/login.ts                 # Review a file
/code-review src/api/ --focus security         # Review directory with security focus
/code-review --diff                            # Review uncommitted changes
/code-review --diff --focus performance        # Review changes for performance
/code-review --receive                         # Handle external review feedback
```

## Source of Truth

- Review command boundaries and output contract: `skills/dev-orchestrator/references/review.md`
- Review agent behavior: `agents/sentinel.md`
- Review quality standards: `skills/code-review/SKILL.md`
- External feedback handling: `skills/code-review/SKILL.md`
- Pipeline review gate: `/workflow-review` and `skills/dev-orchestrator/references/pipeline-operations.md`
