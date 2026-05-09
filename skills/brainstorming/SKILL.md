---
name: Brainstorming
version: "1.0.0"
description: Use before creative development work: new features, behavior changes, UI work, architecture changes, or broad refactors.
---

# Brainstorming

Use this skill to turn an idea into a clear design. The goal is not ceremony; it is to surface assumptions before code makes them expensive.

## Hard Gate

Do not implement until there is an approved design. For tiny work, the design can be two or three sentences. For larger work, write it as a spec.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "It's too simple for a design" | Simple things go wrong in simple ways. A 2-sentence design takes 10 seconds. |
| "I'll figure it out as I code" | That's called debugging, not designing. Design first, code second. |
| "The requirements are already clear" | Clear requirements are not a design. How you implement them is the design. |
| "Design slows us down" | Skipping design guarantees rework. Rework is slower than design. |
| "I can refactor later" | Refactoring a wrong architecture costs 10x more than designing it right. |

## Process

1. **Explore context**
   - Read the relevant README, docs, commands, skills, agents, and nearby code.
   - Note existing patterns the design should respect.

2. **Clarify**
   - Ask one focused question at a time when needed.
   - Prefer multiple-choice questions for ambiguous product or architecture trade-offs.
   - Skip questions when the repo already answers them and the assumption is low risk.

3. **Compare approaches**
   - Present 2-3 viable approaches.
   - Include trade-offs, risks, and a recommendation.
   - Keep the recommendation tied to the existing codebase.

4. **Present the design**
   - Cover scope, files/modules, data flow, error handling, tests, and rollout.
   - Scale detail to risk.
   - Ask for approval before implementation.

5. **Save the spec when the task is substantial**
   - Path: `.claude/flow/designs/<topic>-design.md`
   - Include goals, non-goals, chosen approach, tasks, risks, and verification.

## Design Checks

Before moving on:

- No `TBD`, `TODO`, or vague "handle edge cases" language.
- Requirements are testable.
- The design does not bundle unrelated refactors.
- The smallest useful version is clear.
- Risks have verification steps.

## Handoff

After design approval, use `writing-plans` for multi-step work or the lightweight TDD path for narrow changes.
