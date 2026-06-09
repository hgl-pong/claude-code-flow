---
name: semi-auto
description: Human-approved discovery and planning followed by dynamic workflow execution. Use when user wants a guided non-fully-auto flow.
---

# Semi-Auto

Human-approved discovery, then autonomous workflow execution. For zero-touch runs use `claude-code-flow:auto-mode`.

## Flow

1. Clarify purpose, constraints, success criteria; one question at a time.
2. Research the repo and technical constraints; use researcher/designer prompts when helpful.
3. Present 2-3 approaches with tradeoffs and get approval.
4. Write approved spec to `.claude/specs/YYYY-MM-DD-<feature>-design.md`.
5. Write executable plan to `.claude/plans/YYYY-MM-DD-<feature>-plan.md`.
6. Review spec+plan adversarially; revise until clear.
7. Launch `skills/workflow-driven-development/execute-plan.workflow.js` for non-trivial implementation.
8. Inline only trivial/config-only steps when `Workflow` is unavailable.
9. Finish through `claude-code-flow:finishing-a-development-branch` after gates pass.

## Plan Requirements

Each task needs: `id`, full description, `depends_on`, files, tests, verification, risk, subsystem. High/critical tasks require files/tests/verification. Runtime work needs acceptance refs and smoke evidence.

## Review + Verification

Reviewer behavior is built into the workflow scripts: spec review, code review, final review, and seven gates. Implementation tasks use failing-first tests when behavior changes; docs/config-only tasks use the strongest available static/runtime check.

## Boundaries

- Human approves spec/plan before execution.
- Workflow agents handle implementation/review/fixes after approval.
- Stop for true ambiguity, plan-level scope changes, exhausted recovery, or gate retry cap.
- Do not create PRs unless explicitly requested after the human reviews the diff.
