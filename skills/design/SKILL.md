---
name: Design
version: "1.0.0"
description: "Structured design feedback, handoff specs, system audits, accessibility reviews, UX copy, and design system document production. Trigger with 'review this design', 'critique this mockup', 'handoff spec', 'developer specs', 'design system audit', 'document this component', 'audit accessibility', 'check a11y', 'WCAG check', 'write copy for', 'what should this button say', 'design this UI', 'produce DESIGN.md', 'design tokens', 'color system', or when sharing screenshots, checking consistency, writing microcopy, or preparing designs for engineering."
argument-hint: "[critique | handoff | system | a11y | copy | ui-design] <context>"
---

# Design

Dispatch skill for design-related workflows. Auto-detect mode from context or use explicit argument.

## Modes

| Mode | Trigger | Reference |
|------|---------|-----------|
| **critique** | "review this design", "critique this mockup", "what do you think of this UI" | `design-critique.md` |
| **handoff** | "handoff spec", "developer specs", "implement this design" | `design-handoff.md` |
| **system** | "design system audit", "document this component", "new component that fits" | `design-system.md` |
| **a11y** | "audit accessibility", "check a11y", "is this accessible", "WCAG check" | `accessibility-review.md` |
| **copy** | "write copy for", "what should this button say", "review this error message" | `ux-copy.md` |
| **ui-design** | "design this UI", "produce DESIGN.md", "design tokens", "color system", "type scale" | `ui-design.md` (+ 5 supporting refs) |

## Auto-Detection

- Screenshot or Figma link + "review/feedback/critique" → critique
- Design ready for engineering → handoff
- Consistency, tokens, components, naming → system
- Contrast, keyboard, WCAG, a11y → a11y
- Button text, error message, microcopy → copy
- DESIGN.md, design tokens, color/type/spacing system → ui-design

## Reference Files

Each mode has a detailed workflow and output template:

- **Critique**: See `references/design-critique.md` for five-dimension feedback framework, severity levels, and structured output template
- **Handoff**: See `references/design-handoff.md` for specification sections, edge cases, and handoff template
- **System**: See `references/design-system.md` for audit/document/extend modes, token coverage checklist, and component specs
- **A11y**: See `references/accessibility-review.md` for WCAG 2.1 AA quick reference, testing approach, and audit output template
- **Copy**: See `references/ux-copy.md` for copy patterns, voice/tone guidance, and output template
- **UI Design**: See `references/ui-design.md` for 6-phase DESIGN.md production (color/type/spacing/icon/elevation/radius/transition systems, component states, layout composition). Also loads `references/anti-ai-design.md`, `references/design-knowledge-base.md`, `references/design-md-spec.md`, `references/layout-patterns.md`, `references/ui-research-brief.md` for knowledge base.

## If Connectors Available

If **~~image-gen** is connected:
- Use `img describe` to analyze screenshots for layout, color, typography, and contrast details
- Generate annotated screenshots highlighting issues, token boundaries, or state differences

If **~~code-intel** is connected:
- Run `gitnexus_query` to find component usage across the codebase (system mode)
- Run `gitnexus_impact` before renaming tokens to assess blast radius (system mode)

If **~~browser** is connected:
- Navigate to running app to visually verify design implementation against DESIGN.md tokens
- Screenshot pages for critique mode instead of requiring user-provided screenshots

## Tips

- Specify the design stage (exploration, wireframe, hi-fi, final polish) — feedback depth should match.
- Pair handoff with a DESIGN.md if the project has one — reference its tokens directly.
- Run a11y audit after design changes that affect color, layout, or interactive elements.
- Audit the design system before extending it — understand the current state first.
- Read copy aloud. If it sounds robotic, rewrite it. Test copy in context, not in isolation.
