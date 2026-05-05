---
name: Using Claude Code Flow
version: "1.0.0"
description: "Use at the start of any development conversation to select the right workflow skill before acting."
---

# Using Claude Code Flow

This skill is the entry point for the plugin. Before acting, check whether one of the workflow skills applies.

## Core Rule

If the task might involve code, tests, architecture, debugging, review, documentation, or delivery, pick the matching skill first. User instructions still win.

## Response Style

Default to concise answers. Lead with the result, include only the decisions, files, commands, risks, and next steps the user needs. Do not narrate routine process. Expand only when the user asks for details, when trade-offs are genuinely important, or when a failure/blocker needs explanation.

Routine final replies should usually be 3-6 bullets or 1-2 short paragraphs.

## Skill Selection

| Situation | Use |
|---|---|
| Prompt contains `ulw` or `ultrawork` | `ultrawork` — full autonomous delivery |
| Prompt contains `uli` | `ultrawork` (ULI branch) — product iteration loop |
| New feature, behavior change, refactor, UI work, or multi-file delivery | `brainstorming` first, then `writing-plans` |
| Task needs planning, sequencing, or cross-agent coordination | `workflow-plan` (or `/plan`, which maps here) |
| Multi-step implementation with approved plan | `dev-orchestrator` |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with TDD cycle |
| Code review request | `code-quality` and `sentinel` |
| "Is it done?" or final delivery | `verification-before-completion` |
| Plan or design already approved, need execution | `writing-plans` then `dev-orchestrator` |
| User asks for "plan mode" or `/plan` | `workflow-plan` |


## Priority

When multiple skills apply, run them in this order:
1. Process skills first (brainstorming, systematic-debugging) — determines HOW to approach
2. Implementation skills second (testing-strategy, dev-orchestrator) — guides execution
3. Verification skills last (verification-before-completion) — confirms delivery

**ULW exception:** In `ultrawork` mode the approval gates are automatically bypassed — but verification evidence and test-first are still mandatory.
