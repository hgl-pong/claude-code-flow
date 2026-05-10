# UI Research Brief

Data requirements for the UI research phase (Gate 5). Research subagents use this as the "what to gather" spec.

## Local Codebase Audit

1. Existing UI components, styling patterns, design tokens, theme configuration
2. Component library (if any), CSS framework, icon system
3. Current color palette, typography choices, spacing conventions
4. Existing DESIGN.md — summarize current tokens and patterns
5. CSS/styling approach: Tailwind, CSS Modules, styled-components, vanilla CSS
6. Actual font imports/declarations and color CSS variables in use

## Competitor Analysis

For each competing/similar product (2-3 total), gather:

1. **Color palette**: hex values if visible, or temperature (warm/cool) and hierarchy (surface, text, accent)
2. **Typography**: font families, size scale approach, heading/body pairing
3. **Layout**: main dashboard structure, navigation (sidebar/top nav/hybrid), content density
4. **Component personality**: button style (rounded/filled/outlined), card treatment, form layout
5. **Distinguishing element**: the ONE visual element that makes it recognizable
6. **Spacing rhythm**: tight/medium/generous

Search queries: "[competitor] design system", "[competitor] UI redesign", "[competitor] interface analysis"

## Design Intelligence

Gather concrete values — no abstract descriptions.

### Typography
- 2-3 font pairings used by quality products in this domain
- Type scale ratios: 1.2x, 1.25x, 1.333x?
- Base body font size: 13px (dev tools), 16px (content), 18px (editorial)

### Color
- Color families dominating this domain (e.g. fintech: teal/navy, dev: green/cyan)
- Dark mode adoption: which competitors offer it, how handled
- Accent strategy: single accent or multi-accent? Semantic or brand colors?

### Layout
- Grid system: 12-col dashboard, 8-col editorial, asymmetric landing
- Navigation pattern: top nav, sidebar, or hybrid
- Content density: tight (Linear-style) or generous (Notion-style)

### Interaction
- Animation patterns: subtle transitions, scroll-triggered, or none
- Loading states: skeleton, spinner, progressive
- Empty state treatment: functional or personality-driven
