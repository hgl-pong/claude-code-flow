---
name: Using Claude Code Flow
version: "2.1.0"
description: "Use once as a workflow router when no command, hook, or active skill has already selected the path. Skip for subagents and for tasks already routed to workflow-plan, brainstorm, write-plan, execute-plan, quick-fix, or dev-orchestrator."
argument-hint: "<task description>"
---

# Using Claude Code Flow

<SUBAGENT-STOP>
If dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

## Invocation Rule

Use this skill as a **single routing pass**, not as a recurring companion skill.

Invoke it only when the entry path is unclear. If a slash command, hook hint, active workflow phase, or already-loaded skill has selected a primary route, follow that route directly and do not re-invoke this skill just to confirm.

Skill check comes before substantive work, but it should produce one primary route plus any explicitly required companion skills. It should not create a `using-claude-code-flow -> workflow-plan -> using-claude-code-flow -> brainstorming` loop.

## Instruction Priority

1. **User's explicit instructions** (CLAUDE.md, direct requests) - highest
2. **Plugin skills** - override default behavior where they conflict
3. **Default system prompt** - lowest

## De-Dupe Guard

Do not invoke this skill again when any of these is already true:

- The prompt starts with `/plan`, `/workflow-plan`, `/brainstorm`, `/write-plan`, `/execute-plan`, or `/quick-fix`.
- A hook already says `Primary skill:` or routes to a specific workflow skill.
- You are inside `workflow-plan`, `brainstorming`, `writing-plans`, `executing-plans`, `quick-fix`, or `dev-orchestrator`.
- The task is an approved plan/spec moving into execution.

In those cases, treat the selected command or skill as authoritative and continue with its local checklist.

## Red Flags - STOP and Check Skills

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks, but one routing pass is enough. |
| "I need more context first" | Do one skill route check before substantive exploration. |
| "Let me explore the codebase first" | Skills tell you how to explore. Check first when no route exists. |
| "This doesn't need a formal skill" | If a skill clearly applies, use it. |
| "I remember this skill" | Skills evolve. Read the current version when invoked. |
| "I'll just re-check the route" | Do not loop through this skill after a route is active. |

## Skill Selection

| Situation | Use |
|---|---|
| Prompt contains `ulw` or `ultrawork` | `ultrawork` - full autonomous delivery |
| Prompt contains `uli` | `ultrawork` (ULI branch) - product iteration loop |
| Ambiguous new feature, substantial behavior change, UI/architecture decision, broad refactor, or exploratory product work | `brainstorming`, then `writing-plans` only if execution needs a task plan |
| Task primarily asks for a proposal, plan, sequencing, approval gate, or cross-agent coordination | `workflow-plan` |
| Task references another repo/plugin/agent pack/workflow as inspiration or source material | `workflow-intake` before `workflow-plan` |
| User asks to implement, build, fix, refactor, ship, deliver, or execute work | `dev-orchestrator` after any required process skill |
| Multi-step implementation, approved plan, cross-file change, full-stack task, or end-to-end fix | `dev-orchestrator` |
| Large task with 3+ subtasks needing parallel agent dispatch | `dev-orchestrator`, which invokes `dispatching-parallel-agents` |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with TDD cycle |
| Code review request | `code-quality` and `sentinel` |
| "Is it done?" or final delivery | `verification-before-completion` |
| Plan or design already approved, need execution | `dev-orchestrator`; use `writing-plans` only if no executable task plan exists |
| User asks for "plan mode" or `/plan` | `workflow-plan` |
| Built-in plan appears relevant | prefer `workflow-plan`, avoid `EnterPlanMode` |
| Implementation complete, tests pass | `finishing-branch` |
| Received code review feedback | `receiving-code-review` |
| Creating or editing a skill | `writing-skills` |

## Skill Priority

When multiple skills apply:

1. **Primary route first** - choose one owner (`workflow-plan`, `brainstorming`, `quick-fix`, or `dev-orchestrator`).
2. **Process skills second** - use `brainstorming` or `systematic-debugging` only when their trigger conditions are met.
3. **Implementation skills third** - use `testing-strategy` and `dev-orchestrator` for code delivery.
4. **Verification skills last** - use `verification-before-completion` before final delivery.

## Response Style

Concise. Lead with the result. Include only decisions, files, commands, risks, and next steps. Expand only for trade-offs or failure explanation. Default: 3-6 bullets or 1-2 short paragraphs.

**ULW exception:** In `ultrawork` mode approval gates are bypassed; verification evidence and test-first are still mandatory.
