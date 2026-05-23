# Research Dispatch Templates

Templates for dispatching research subagents via `general-purpose` type. Each template includes the Iron Law inline — subagents need no other context files.

## Technical Research

```
Agent({
  description: "Research: [topic]",
  subagent_type: "general-purpose",
  prompt: """
Research [topic] and produce a structured report.

## Research Rules

- NEVER fabricate information. If you cannot find it, say so.
- Cross-reference 2+ sources for claims affecting development decisions.
- Single-source claims must be flagged as "unverified — single source".
- NEVER write to source code files. Write research outputs only.
- Confidence levels:
  - High: 2+ authoritative sources agree, published <1yr, confirmed locally
  - Medium: 1+ corroborating source, OR authoritative source >1yr old
  - Low: single source, conflicting sources, OR unable to verify
  - Local: verified by reading local code directly

## Phase 1: Clarify Scope

1. State the research question explicitly
2. Define what outputs the consumer (oracle/forge/user) needs
3. Identify constraints: versions, platforms, licensing, bundle size, compatibility

## Phase 2: Local Codebase Analysis

1. Inventory — scan [relevant paths] for existing patterns, utilities, abstractions
2. Dependencies — check package manifest for current deps related to [topic]
3. Conventions — identify coding patterns, naming, error handling in use
4. Constraints — architectural boundaries, banned patterns, performance requirements
5. Gaps — what's missing that the task requires but doesn't exist yet?
6. Interfaces — what existing APIs/types must the new work conform to?

## Phase 3: External Research

1. [specific external question — APIs, libraries, best practices, etc.]
2. [specific external question]
3. [specific external question]

For library comparisons: check GitHub stars, last commit date, open issues, breaking changes.
For API evaluation: check rate limits, pricing, authentication, SDK maturity.

## Phase 4: Synthesis

1. Merge local + external findings — where they align, conflict, or complement
2. Assign confidence per finding
3. Produce ranked recommendations with trade-offs
4. Flag open questions that research alone cannot resolve

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/research-[topic].md`]

Structure as:
1. **Research Question** — what was investigated and why
2. **Local Context** — existing code, patterns, dependencies, constraints, gaps
3. **External Findings** — per-finding: topic, result, sources (URLs), confidence
4. **Comparison** (if evaluating options) — side-by-side with decision criteria
5. **Recommendations** — ranked, with trade-offs and confidence
6. **Open Questions** — what couldn't be determined
"""
})
```

## UI Research (frontend-UI tasks)

Use when Gate 5 (UI Research) is checked. Dispatch BEFORE UI Design step. See `skills/design/references/` for design domain knowledge.

```
Agent({
  description: "UI Research: [product/domain]",
  subagent_type: "general-purpose",
  prompt: """
Produce a UI research report for [product/domain].

## Research Rules

- NEVER fabricate information. If you cannot find it, say so.
- Cross-reference 2+ sources for claims.
- NEVER write to source code files. Write research outputs only.
- Gather SPECIFIC concrete values (hex codes, font names, px values) — not abstract descriptions.

Confidence levels:
- High: 2+ authoritative sources agree, published <1yr, confirmed locally
- Medium: 1+ corroborating source, OR authoritative source >1yr old
- Low: single source, conflicting sources, OR unable to verify
- Local: verified by reading local code directly

## Phase 1: Local Codebase Analysis

1. Explore existing UI components, styling patterns, design tokens, theme configuration
2. Identify component library (if any), CSS framework, icon system
3. Note existing color palette, typography choices, spacing conventions
4. Check for existing DESIGN.md — summarize its current tokens and patterns
5. Identify the CSS/styling approach: Tailwind, CSS Modules, styled-components, vanilla CSS, etc.
6. Find the actual font imports/declarations and color CSS variables in use

## Phase 2: Current Aesthetic Trends (MANDATORY)

Research what the design world looks like RIGHT NOW:
1. Current visual trends — use current year and next year in queries (e.g. "UI design trends {this year} {next year}"). Search "UI design trends", "web design trends"
2. Typography trends — search "typography trends" + current year, "best web fonts" + current year
3. Color direction — search "color trends UI" + current year, "design color palette trends"
4. Layout evolution — search "app layout trends" + current year, "dashboard design trends"
5. Interaction patterns — search "UI animation trends" + current year, "microinteraction design trends"

## Phase 3: Competitor Analysis

Research 2-4 competing/similar products. For EACH product, gather:
1. Visual first impression — what's the IMMEDIATE feeling?
2. Color palette: hex values or temperature + hierarchy. What color FAMILY dominates and WHY?
3. Typography: font families (identify them!), size scale, heading/body pairing
4. Layout: main dashboard structure, navigation, content density, grid system
5. Component personality: button/card/form/modal style
6. Spacing rhythm: tight/medium/generous with px values if possible
7. Distinguishing element: ONE visual element that makes it recognizable
8. Strengths to borrow vs weaknesses to avoid
9. Mobile experience: how does the design adapt?

Search: "[competitor] design system", "[competitor] UI redesign", "[competitor] interface analysis"

After all competitors: comparative summary — shared visual language (table stakes) vs differentiators (opportunity space).

## Phase 4: Design Intelligence

Gather concrete data (not abstract descriptions):
- **Typography**: 2-3 font pairings, type scale ratios, base body font size
- **Color**: dominant color families, dark mode adoption, accent strategy
- **Layout**: grid system, navigation pattern, content density
- **Interaction**: animation patterns, loading states, empty state treatment

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/ui-research.md`]

Structure as:
- **Trend Context**: what aesthetics are current right now
- **Local findings**: existing design system, tokens, component inventory
- **Competitor analysis**: per-product breakdown with SPECIFIC visual values
- **Comparative summary**: shared language vs differentiators
- **Design intelligence**: concrete data for this domain
- **Design direction recommendations**: 2-3 directions with fonts, colors, density, reference products
"""
})
```

## Product Analysis

For ULI product iteration analysis. Also works outside ULI — if ULI state files don't exist, skip step 1 and analyze from README only.

```
Agent({
  description: "Product analysis: [product]",
  subagent_type: "general-purpose",
  prompt: """
Produce a product analysis report for [product].

## Research Rules

- NEVER fabricate information. If you cannot find it, say so.
- Cross-reference 2+ sources for claims.
- NEVER write to source code files. Write research outputs only.

## Input (read in this order)

1. `.claude/flow/uli/product-state.md` — goal + completed features (skip if doesn't exist)
2. `.claude/flow/uli/<slug>/acceptance-report.md` — last verdict + gaps (skip if doesn't exist)
3. `.claude/flow/designs/` — latest spec
4. `git log --oneline -20` — recent commits
5. Project README — product domain

If ULI state files don't exist, analyze from README and recent commits only.

## Scope Guard

- Do not re-propose completed features
- If gap list is non-empty, highest-priority gap comes first
- Max 3 recommended areas — defer extras

## Output

Write analysis to `.claude/flow/uli/<slug>/analysis.md` (or `[output_path]` if non-ULI)

Structure as:
- Product State Summary
- Gap Analysis
- Top 3 Recommendations
- Constraints
"""
})
```
