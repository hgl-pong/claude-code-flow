---
name: Using Claude Code Flow
version: "1.0.0"
description: "Entry point skill. Use at the start of any development conversation to select the right workflow skill before acting."
---

# Using Claude Code Flow

This skill is the entry point for the plugin. Before acting, check whether one of the workflow skills applies.

## Core Rule

If the task might involve code, tests, architecture, debugging, review, documentation, or delivery, pick the matching skill first. User instructions still win.

## Skill Selection

| Situation | Use |
|---|---|
| Prompt contains `ulw` or `ultrawork` | `ultrawork` — full autonomous delivery |
| Prompt contains `uli` | `ultrawork` (ULI branch) — product iteration loop |
| New feature, behavior change, refactor, UI work | `brainstorming` first, then `writing-plans` |
| Multi-step implementation with approved plan | `dev-orchestrator` |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with TDD cycle |
| Code review request | `code-quality` and `sentinel` |
| "Is it done?" or final delivery | `verification-before-completion` |

**ULW exception:** In `ultrawork` mode the approval gates are automatically bypassed — but verification evidence and test-first are still mandatory.
