---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
---

# Brainstorming Ideas Into Designs

Turn ideas into approved specs before implementation.

<HARD-GATE>
Do NOT invoke implementation skills, write/scaffold code, or modify behavior until you present a design and the user approves it. Applies even to “simple” work.
</HARD-GATE>

## Checklist

Create tasks for these and complete in order:

1. Explore project context: files/docs/recent commits.
2. If upcoming questions are visual, offer Visual Companion in its own message only.
3. Ask clarifying questions one at a time; understand purpose, constraints, success criteria.
4. After requirements are clear, dispatch researcher with `skills/workflow-driven-development/researcher-prompt.md`; save `.claude/research/<task-name>/<type>-research.md` (`product-research`, `market-research`, or `feasibility-research`). Read before approaches.
5. If visible UI/pages/components/styling/layout/interaction/states: designer writes `.claude/research/<task-name>/ui-research.md` + root `DESIGN.md`; design reviewer (`skills/workflow-driven-development/design-reviewer-prompt.md`) approves; loop until approved.
6. Propose 2-3 approaches with tradeoffs; recommend one; cite research artifacts.
7. Present design in complexity-scaled sections; get approval after each section.
8. Write spec: `.claude/specs/YYYY-MM-DD-<topic>-design.md` unless user preference overrides.
9. Spec reviewer loop: check placeholders, contradictions, ambiguity, scope creep, missing citations, research alignment. Revise until approved.
10. Commit reviewed design doc.
11. Ask user to review spec file before planning.
12. Only after user approves spec, invoke `claude-code-flow:writing-plans`.

Terminal state: `writing-plans`. Do not invoke other implementation skills from brainstorming.

## Scope Guard

If request spans independent subsystems (chat + storage + billing + analytics, etc.), stop early and decompose. Brainstorm first sub-project through normal spec → plan → implementation.

## Question Rules

- One question per message.
- Multiple choice preferred when useful.
- Focus on purpose/constraints/success criteria.
- If research reveals conflicts or unresolved ambiguity, ask before continuing.

## Design Content

Cover only what matters for the task: architecture, components, data flow, error handling, tests. Scale: a few sentences for straightforward work; 200-300 words for nuanced sections.

Design for isolation: small units, clear interfaces, explicit dependencies, testable boundaries. In existing code, follow patterns; include only targeted cleanup needed for the goal.

## Visual Companion

The visual companion is also called the brainstorm server / design viewer and may use localhost browser views. Offer only when visual content will help (mockups, wireframes, layout comparisons, architecture diagrams):

> Some of what we're working on might be easier to explain if I can show it to you in a web browser. I can put together mockups, diagrams, comparisons, and other visuals as we go. This feature is still new and can be token-intensive. Want to try it? (Requires opening a local URL)

The offer must be the entire message. If accepted, use browser only per-question when seeing beats reading. UI topic ≠ automatically visual. For details only then read `skills/brainstorming/visual-companion.md`.

## Key Principles

YAGNI ruthlessly. Explore alternatives. Validate incrementally. Ask when confusing. Research before approaches. Approved `DESIGN.md` binds downstream UI implementation.
