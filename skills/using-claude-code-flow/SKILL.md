---
name: Using Claude Code Flow
version: "2.0.0"
description: "Use when starting any task"
---

# Using Claude Code Flow

<SUBAGENT-STOP>
If dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

## Invocation Rule

If there is even a 1% chance a skill might apply, invoke it. Skill check comes BEFORE any response — including clarifying questions.

## Instruction Priority

1. **User's explicit instructions** (CLAUDE.md, direct requests) — highest
2. **Plugin skills** — override default behavior where they conflict
3. **Default system prompt** — lowest

## Red Flags — STOP and Check Skills

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |

## Skill Selection

| Situation | Use |
|---|---|
| Prompt contains `ulw` or `ultrawork` | `ultrawork` — full autonomous delivery |
| Prompt contains `uli` | `ultrawork` (ULI branch) — product iteration loop |
| New feature, behavior change, refactor, UI work, or multi-file delivery | `brainstorming` first, then `writing-plans` |
| Task needs planning, sequencing, or cross-agent coordination | `workflow-plan` |
| Multi-step implementation with approved plan | `dev-orchestrator` |
| Large task with 3+ subtasks needing parallel agent dispatch | `dispatching-parallel-agents` (invoked by dev-orchestrator) |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with TDD cycle |
| Code review request | `code-quality` and `sentinel` |
| "Is it done?" or final delivery | `verification-before-completion` |
| Plan or design already approved, need execution | `writing-plans` then `dev-orchestrator` |
| User asks for "plan mode" or `/plan` | `workflow-plan` |
| Built-in plan appears relevant | prefer `workflow-plan`, avoid `EnterPlanMode` |
| Implementation complete, tests pass | `finishing-branch` |
| Received code review feedback | `receiving-code-review` |
| Creating or editing a skill | `writing-skills` |

## Skill Priority

When multiple skills apply:
1. **Process skills first** (brainstorming, systematic-debugging) — determines HOW to approach
2. **Implementation skills second** (testing-strategy, dev-orchestrator) — guides execution
3. **Verification skills last** (verification-before-completion) — confirms delivery

## Response Style

Concise. Lead with the result. Include only decisions, files, commands, risks, and next steps. Expand only for trade-offs or failure explanation. Default: 3-6 bullets or 1-2 short paragraphs.

**ULW exception:** In `ultrawork` mode approval gates are bypassed — verification evidence and test-first are still mandatory.
