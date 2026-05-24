---
name: brainstorming
description: "Brainstorm ambiguous features, product ideas, UI/architecture choices, broad refactors, PRDs, specs, and assumptions before code. Use when the user asks to brainstorm, explore options, write a PRD/spec, choose architecture/UI direction, or clarify a new feature; skip approved/direct implementation."
---

# Brainstorming

Turn ambiguity into an approved direction before implementation.

## Rules

- Do not implement until the user approves a direction or spec.
- Keep tiny work to a short decision note; use a fuller spec only when decisions are numerous or risky.
- Name assumptions, tradeoffs, open questions, and the recommended path.
- If a command/hook already routed to planning/execution, do not re-route back here.

## Workflow

1. Restate the goal and visible constraints.
2. Identify the real decision points.
3. Offer 2-4 viable options with tradeoffs.
4. Recommend one option and explain why.
5. Ask only blocking questions.
6. After approval, hand off to planning or dev-orchestrator.

## Outputs

- Problem / goal
- Options / tradeoffs
- Recommendation
- Open questions or approval needed

## References

Read only when needed:

- `references/write-spec.md` - spec-writing workflow for approved directions.
