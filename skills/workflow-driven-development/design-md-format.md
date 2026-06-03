# DESIGN.md Format Reference

Root `DESIGN.md` is a developer-usable UI/UX design system spec. It is not a pitch, architecture overview, component inventory, or data-model doc. It must be specific enough that an implementation agent can build without guessing.

Save `DESIGN.md` at project root only after `.claude/research/<task-name>/ui-research.md` exists.

## Required Structure

```markdown
# Design System: [Project Name]

**Version:** 1.0
**Date:** [YYYY-MM-DD]
**Direction:** [1-2 sentences: warm/cool, dense/airy, playful/serious, key differentiator]

## Research Summary
- Summarize `.claude/research/<task-name>/ui-research.md`
- Include source-backed conclusions with URLs/access dates from the research file
- Identify patterns users expect, differentiating choices, and rejected alternatives
- Every major design decision below must cite the specific research finding that supports it

## Token Architecture

### Primitive Tokens
Raw values only. No aliases.

### Semantic Tokens
Meaning-based aliases that map to primitive tokens.
Use names like `surface-*`, `text-*`, `border-*`, `accent-*`, `danger-*`, `success-*`.

### Component Tokens
Component-scoped tokens that map to semantic tokens.
Use names like `button-*`, `input-*`, `card-*`, `modal-*`.

## Theme Groups
Define the active variation axes and the token changes each axis controls.
Each theme option must list exact token overrides or explicitly say "no token changes".

### color-scheme
Light / dark token sets. For each option, list changed semantic/component tokens.

### breakpoint
Mobile / tablet / desktop / wide layout tokens. For each option, list layout token changes.

### contrast
Normal / high-contrast accessibility variants. For each option, list contrast-related token changes.

## Component Specs
Define each interactive component in a way developers can implement exactly.

### Component: [Name]
- **Variants:** [size, intent, tone, or other meaningful variants]
- **States:** default, hover, active, focus, disabled, loading, error
- **Variant × State Matrix:** required table; each cell must reference component/semantic tokens, not prose adjectives
- **Visual Contract:** padding, radius, typography, border, shadow, cursor, motion, and icon/content rules as token references
- **Behavior Notes:** only if needed for ambiguity, keyboard, or content rules

## Layout & Composition
- Grid and content width
- Page gutter and section rhythm
- Card / panel composition rules
- Any layout-specific token usage

## Breakpoints
- Define each breakpoint name and min/max width
- State what layout changes at each breakpoint
- Do not leave breakpoint behavior implicit

## Accessibility
- Contrast ratios: body text/background pairs ≥ 4.5:1 and large text/icons ≥ 3:1 (WCAG AA minimum)
- Focus: visible keyboard focus ring on all interactive elements, specified with token references
- Touch: minimum 44px touch targets for pointer/touch controls
- States: no color-only state indicators; pair color with icon, text, border, or shape change
- Screen reader or announcement notes if relevant
- Motion: respect prefers-reduced-motion and define reduced alternatives for non-essential animation

## Decision Traceability
- Map each major token family, layout choice, and component state rule back to the research summary
- If a decision is an exception to common patterns, say why
```

## Quality Checklist

Before reporting done:
- [ ] UI research saved to `.claude/research/<task-name>/ui-research.md` with 3+ competitors, URLs, and access dates
- [ ] DESIGN.md uses the required structure above
- [ ] Research summary includes source-backed conclusions with URLs/access dates from ui-research.md
- [ ] Token architecture is split into primitive, semantic, and component layers
- [ ] Theme groups cover color-scheme, breakpoint, and contrast with exact token overrides or explicit "no token changes"
- [ ] Component specs include variants, states, required Variant × State Matrix, and token-backed Visual Contract
- [ ] Breakpoints state exact layout changes
- [ ] Accessibility section includes numeric WCAG contrast targets, focus tokens, 44px touch minimums, non-color state indicators, and reduced-motion behavior
- [ ] Major decisions are traceable back to research
- [ ] DESIGN.md saved to project root

## Failure Modes

| Failure | Fix |
|---------|-----|
| No research | Phase 1 is mandatory before tokens |
| Flat tokens | Use primitive, semantic, and component layers |
| AI defaults | Every token family needs a decision rationale |
| Missing states | Every interactive component needs the full state set |
| Vague usage | Say exact context: "Primary submit button", not "buttons" |
| Implicit responsiveness | State the layout change for each breakpoint |
| Token-only thinking | Include layout, component specs, and accessibility |
| Prose-only component spec | Add Variant × State Matrix and token-backed Visual Contract |
