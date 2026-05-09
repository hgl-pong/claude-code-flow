---
name: Brainstorming
version: "2.0.0"
description: "Use when creating features, building components, adding functionality, or modifying behavior — before implementation"
---

# Brainstorming

Turn ideas into clear designs. The goal is not ceremony — it is to surface assumptions before code makes them expensive.

## Hard Gate

Do not implement until there is an approved design. For tiny work, the design can be two or three sentences. For larger work, write it as a spec.

This applies to EVERY task regardless of perceived simplicity. "Simple" projects are where unexamined assumptions cause the most wasted work.

## Anti-Pattern: "Too Simple To Need Design"

| Excuse | Reality |
|--------|---------|
| "It's too simple for a design" | Simple things go wrong in simple ways. A 2-sentence design takes 10 seconds. |
| "I'll figure it out as I code" | That's called debugging, not designing. Design first, code second. |
| "The requirements are already clear" | Clear requirements are not a design. How you implement them is the design. |
| "Design slows us down" | Skipping design guarantees rework. Rework is slower than design. |
| "I can refactor later" | Refactoring a wrong architecture costs 10x more than designing it right. |

## Process

1. **Explore context**
   - Read relevant README, docs, commands, skills, agents, and nearby code.
   - Note existing patterns the design should respect.
   - If the request describes multiple independent subsystems, flag this immediately. Help decompose into sub-projects before refining details.

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
   - Design for isolation: break into units with clear purpose, well-defined interfaces, understandable independently.
   - Ask for approval before implementation.

5. **Save the spec when substantial**
   - Path: `.claude/flow/designs/<topic>-design.md`
   - Include goals, non-goals, chosen approach, tasks, risks, and verification.

## Spec Self-Review

After writing the spec document, check before asking user to review:

- **Placeholder scan** — Any `TBD`, `TODO`, incomplete sections, or vague "handle edge cases"? Fix them.
- **Internal consistency** — Do sections contradict each other? Does architecture match feature descriptions?
- **Scope check** — Focused enough for a single implementation plan? Or needs decomposition?
- **Ambiguity check** — Could any requirement be interpreted two ways? Pick one, make explicit.
- **No bundled refactors** — Design does not include unrelated changes.
- **Testable requirements** — Every requirement can be verified.
- **Risks have verification steps.**

Fix inline. No need to re-review — just fix and move on.

## User Review Gate

After spec self-review passes:

> "Spec written to `<path>`. Please review before we write the implementation plan."

Wait for user response. If changes requested, make them and re-run self-review. Only proceed once approved.

## Handoff

After approval, invoke **SUGGESTED: `writing-plans`** for multi-step work or the lightweight TDD path for narrow changes. Do not invoke any implementation skill directly.
