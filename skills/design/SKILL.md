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

## Design Viewer (ui-design mode only)

After producing or updating DESIGN.md, offer the user an interactive visual editor:

> DESIGN.md has been produced. Would you like to open the **Design Viewer** to visually inspect and adjust tokens (colors, typography, spacing, etc.) in a browser?

If the user agrees, run:
```bash
python hooks/scripts/design-server.py
```
Then tell the user: **Open http://localhost:8765 in your browser** to edit tokens visually. Changes save directly back to DESIGN.md.

The viewer parses DESIGN.md tables, renders live previews (buttons, cards, inputs, headings), and lets the user tweak values with color pickers, sliders, and text fields.

**When NOT to offer:**
- Non-interactive session (CI, headless, piped)
- User is in a hurry and explicitly skips review
- DESIGN.md was not produced or updated

## If Connectors Available

If **~~browser** is connected:
- Navigate to running app to visually verify design implementation against DESIGN.md tokens
- Screenshot pages for critique mode instead of requiring user-provided screenshots

## Tips

- Specify the design stage (exploration, wireframe, hi-fi, final polish) — feedback depth should match.
- Pair handoff with a DESIGN.md if the project has one — reference its tokens directly.
- Run a11y audit after design changes that affect color, layout, or interactive elements.
- Audit the design system before extending it — understand the current state first.
- Read copy aloud. If it sounds robotic, rewrite it. Test copy in context, not in isolation.
