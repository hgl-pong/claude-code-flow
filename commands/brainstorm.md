---
name: brainstorm
description: Refine a rough feature, refactor, or architecture idea into an approved design before implementation.
---

# Brainstorm

Use the `brainstorming` skill to turn the request into a clear design.

## Arguments

```
/brainstorm <idea or task>
```

## Process

1. Treat `/brainstorm` as the selected route; do not invoke `using-claude-code-flow` again unless no route context exists.
2. Use `brainstorming`.
3. Explore the project context relevant to the idea.
4. Ask only the clarifying questions needed to remove risky ambiguity.
5. Present 2-3 approaches with trade-offs and a recommendation.
6. Present the chosen design for approval.
7. For substantial work, save the spec to `.claude/flow/designs/<topic>-design.md`. This is a design spec — DESIGN.md (visual design system) goes to project root.

## Output

- Approved design or next clarification question.
- Spec path when one is written.
- Recommended next step: `/write-plan` or lightweight TDD implementation.
