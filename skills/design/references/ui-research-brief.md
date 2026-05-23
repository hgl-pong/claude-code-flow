# UI Research Brief

Data requirements for the UI research phase (Gate 5). Research subagents use this as the "what to gather" spec.

## Local Codebase Audit

1. Existing UI components, styling patterns, design tokens, theme configuration
2. Component library (if any), CSS framework, icon system
3. Current color palette, typography choices, spacing conventions
4. Existing DESIGN.md — summarize current tokens and patterns
5. CSS/styling approach: Tailwind, CSS Modules, styled-components, vanilla CSS
6. Actual font imports/declarations and color CSS variables in use

## Current Aesthetic Trends (MANDATORY)

Research what the design world looks like RIGHT NOW, not what was popular 2 years ago:

1. **Current visual trends** — what aesthetics are trending? (e.g. bento grids, glass morphism evolution, brutalist typography, warm minimalism, AI-era anti-generic). Use the current year and next year in search queries (e.g. "UI design trends {this year} {next year}"). Search "UI design trends", "web design trends", "product design aesthetic trends".
2. **Typography trends** — what typefaces and pairings are top products shipping? Is serif-in-UI growing? What happened to Inter/Roboto dominance? Search "typography trends" + current year, "best web fonts" + current year.
3. **Color direction** — what color families are emerging? Is the blue/purple era ending? What's replacing it? Search "color trends UI" + current year, "design color palette trends".
4. **Layout evolution** — how are leading apps structuring their interfaces? Search "app layout trends" + current year, "dashboard design trends".
5. **Interaction patterns** — micro-interactions, animation direction, hover behaviors in modern apps. Search "UI animation trends" + current year, "microinteraction design trends".

Deliverable: a "Trend Context" section that anchors design decisions in what's current, not what's generic.

## Competitor Analysis

Research 2-4 competing/similar products. For EACH product, gather:

1. **Visual first impression** — screenshot or detailed description of the homepage/main screen. What's the IMMEDIATE feeling?
2. **Color palette**: hex values if visible, or temperature (warm/cool) and hierarchy (surface, text, accent). What color FAMILY dominates and WHY does it work for their domain?
3. **Typography**: font families (identify them!), size scale approach, heading/body pairing, any unusual type choices
4. **Layout**: main dashboard structure, navigation (sidebar/top nav/hybrid), content density, grid system
5. **Component personality**: button style (rounded/filled/outlined), card treatment, form layout, modal style
6. **Spacing rhythm**: tight/medium/generous — quantify if possible (e.g. "8px base unit, generous 32px section gaps")
7. **Distinguishing element**: the ONE visual element that makes it recognizable at a glance
8. **Strengths to borrow**: what they do better than competitors
9. **Weaknesses to avoid**: what feels generic, dated, or poorly executed
10. **Mobile experience** (if available): how does the design adapt?

Search queries: "[competitor] design system", "[competitor] UI redesign", "[competitor] interface analysis", "[competitor] vs alternatives UI"

After analyzing all competitors, produce a **comparative summary**: what visual language is shared across competitors (table stakes) vs what differentiates the best ones (opportunity space).

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
