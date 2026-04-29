---
name: Using Claude Code Flow
version: "1.0.0"
description: Use at the start of any development conversation to select the right workflow skill before planning, implementing, debugging, reviewing, or answering process questions.
---

# Using Claude Code Flow

This skill is the entry point for the plugin. Before acting, check whether one of the workflow skills applies and use it deliberately.

## Core Rule

If the task might involve code, tests, architecture, debugging, review, documentation, or delivery, pick the matching skill first. Do this before implementation and before broad planning.

User instructions still win. If the user explicitly asks for a lightweight answer, no code changes, or a different process, follow that.

## Skill Selection

| Situation | Use |
|---|---|
| Prompt contains `ulw` or `ultrawork` | `ultrawork` — full autonomous delivery, no gates |
| New feature, behavior change, refactor, UI work | `brainstorming` first, then `writing-plans` |
| Multi-step implementation with an approved plan | `dev-orchestrator` or `subagent-driven-development` pattern inside it |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with the TDD cycle |
| Code review request | `code-quality` and `sentinel` |
| "Is it done?" or final delivery | `verification-before-completion` |

## Red Flags

Stop and re-check skills if you catch yourself thinking:

- "This is too small to plan."
- "I'll add tests after."
- "The implementation report says it works."
- "I can skip review because the diff is simple."
- "I need to inspect everything before choosing a process."

**ULW exception:** In `ultrawork` mode the approval gates above are automatically bypassed — but verification evidence is still required, and test-first is still mandatory.

## Process

For small tasks:

1. State the chosen lightweight path.
2. Read the relevant files.
3. Write or identify the failing test first when behavior changes.
4. Make the minimal change.
5. Run the focused verification.
6. Report exact evidence.

For larger tasks:

1. Brainstorm and get design approval.
2. Write an implementation plan with small, testable tasks.
3. Execute through TDD, review, and acceptance gates.
4. Verify before completion.
