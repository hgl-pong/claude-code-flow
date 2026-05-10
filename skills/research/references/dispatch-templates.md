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
- Use `python ~/bin/tavily "query" -n 5` for web searches — NOT the built-in WebSearch tool.
- NEVER write to source code files. Write research outputs only.
- Confidence levels: High (2+ authoritative, agree, <1yr), Medium (1+ corroborating), Low (single/conflicting).

## Phase 1: Local Codebase Analysis

1. Explore existing code in [relevant paths] for related patterns, utilities, and conventions
2. Identify existing abstractions that should be reused
3. Note any constraints or gotchas in the current architecture

## Phase 2: External Research

1. [specific external question — APIs, libraries, best practices, etc.]
2. [specific external question]
3. [specific external question]

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/research-[topic].md`]

Format: concise, actionable, with sources. Structure as:
- **Local findings**: patterns, existing code, constraints
- **External findings**: tools, APIs, best practices, with source URLs
- **Recommendations**: what to consider when planning

Include confidence level per finding.
"""
})
```

## UI Research (frontend-UI tasks)

Use when Gate 5 (UI Research) is checked. Dispatch BEFORE UI Design step. See `skills/ui-design/references/` for design domain knowledge.

```
Agent({
  description: "UI Research: [product/domain]",
  subagent_type: "general-purpose",
  prompt: """
Produce a UI research report for [product/domain].

## Research Rules

- NEVER fabricate information. If you cannot find it, say so.
- Cross-reference 2+ sources for claims.
- Use `python ~/bin/tavily "query" -n 5` for web searches — NOT the built-in WebSearch tool.
- NEVER write to source code files. Write research outputs only.
- Gather SPECIFIC concrete values (hex codes, font names, px values) — not abstract descriptions.

## Phase 1: Local Codebase Analysis

1. Explore existing UI components, styling patterns, design tokens, theme configuration
2. Identify component library (if any), CSS framework, icon system
3. Note existing color palette, typography choices, spacing conventions
4. Check for existing DESIGN.md — summarize its current tokens and patterns
5. Identify the CSS/styling approach: Tailwind, CSS Modules, styled-components, vanilla CSS, etc.
6. Find the actual font imports/declarations and color CSS variables in use

## Phase 2: Competitor Analysis

Research 2-3 competing/similar products. For EACH product, gather:
1. Color palette: hex values or palette temperature and hierarchy
2. Typography: font families, size scale, heading/body pairing
3. Layout patterns: dashboard structure, nav pattern, content density
4. Component personality: button style, card treatment, form layout
5. Distinguishing visual element
6. Spacing rhythm: tight/medium/generous

Search for: "[competitor] design system", "[competitor] UI redesign"

## Phase 3: Design Intelligence

Gather concrete data (not abstract descriptions):
- **Typography**: 2-3 font pairings, type scale ratios, base body font size
- **Color**: dominant color families, dark mode adoption, accent strategy
- **Layout**: grid system, navigation pattern, content density
- **Interaction**: animation patterns, loading states, empty state treatment

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/ui-research.md`]

Structure as:
- **Local findings**: existing design system, tokens, component inventory
- **Competitor analysis**: per-product breakdown with SPECIFIC visual values
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
- Use `python ~/bin/tavily "query" -n 5` for web searches — NOT the built-in WebSearch tool.
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
