---
name: using-claude-code-flow
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If dispatched as a subagent for a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If there is even a 1% chance a skill applies, invoke it before any response/action, including clarifying questions. If a skill applies, you do not have a choice.
</EXTREMELY-IMPORTANT>

## Priority

User instructions (CLAUDE.md/GEMINI.md/AGENTS.md/direct) > Claude Code Flow skills > default prompt. If user instructions conflict with a skill, follow the user.

## Access

Claude Code: use `Skill`. Copilot CLI: use `skill`. Gemini CLI: use `activate_skill`. Never read skill files directly when a skill tool exists.

Non-CC tool mappings live in references: `copilot-tools.md`, `codex-tools.md`, `gemini-tools.md`.

## Rule

Invoke relevant/requested skills before doing anything. If invoked skill is irrelevant after reading, ignore it.

Before `EnterPlanMode`, use `brainstorming` unless already brainstormed.

Priority when multiple apply:
1. Process skills first (`brainstorming`, `systematic-debugging`).
2. Implementation/domain skills second.

Examples: “Build X” → brainstorming first. “Fix bug” → systematic-debugging first.

## After Invoking

Announce: “Using [skill] to [purpose].” If the skill has a checklist, create todos for checklist items. Then follow the skill.

## Red Flags

These are rationalizations: “simple question”, “need context first”, “let me explore the codebase first”, “just check files”, “doesn't need formal skill”, “skill is overkill”, “I remember it”, “not really a task”, “one thing first”. All mean: check skills first.

## Skill Types

Rigid skills (TDD/debugging/verification) must be followed exactly. Flexible pattern skills may be adapted.

Instructions say what; skills say how.
