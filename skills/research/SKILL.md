---
name: Research
version: "1.1.0"
description: "Use when dispatching a research subagent for technical research, library evaluation, product analysis, competitor analysis, or gap analysis. Provides methodology and output standards for general-purpose subagents."
---

# Research

Research subagents are **general-purpose** agents dispatched with inlined methodology. No dedicated agent needed. Research is read-only — dispatch multiple simultaneously with no conflict.

## When to Use

- Technical research: library evaluation, API comparison, best practices investigation
- Product analysis: gap analysis, competitor analysis (ULI mode)
- UI research: competitor visual analysis, design intelligence gathering

**Do NOT use for:** codebase exploration (use gitnexus), simple web lookups (use web-search skill directly), debugging (use systematic-debugging skill).

## Iron Law

**NEVER fabricate information. If you cannot find it, say so. Do not guess.**

Source cross-reference: verify claims with 2+ independent sources. Single-source claims must be flagged as "unverified — single source". NEVER write to source code files.

## Process

1. Clarify scope — what exactly needs to be found and why
2. Formulate targeted search queries (specific, technical, include versions)
3. Cross-reference multiple sources, verify currency (dates, deprecation notices)
4. Prefer official docs, standards, release notes
5. Synthesize structured summary with confidence levels (High/Medium/Low)

Web search: `python ~/bin/tavily "query" -n 5` — NOT the built-in WebSearch tool.

## Common Mistakes

| Failure | Fix |
|---------|-----|
| Single-source claims | Cross-reference or flag as unverified |
| Stale information | Check dates, prefer current sources |
| Scope drift | Stay focused on what was asked |
| Unactionable findings | Include versions, APIs, trade-offs |
| Fabricated URLs | Only cite URLs you actually visited |

## Output

- **Summary**: Key findings + confidence level (High: 2+ authoritative; Medium: 1+ corroborating; Low: single/conflicting)
- **Findings**: Per finding — topic, result, sources, confidence, relevance
- **Comparison** (if applicable): Side-by-side pros/cons
- **Open Questions**: What couldn't be determined

## Dispatching

See `references/dispatch-templates.md` for prompt templates (Technical Research, UI Research, Product Analysis). Templates inline the Iron Law and methodology — no need for subagents to read this file.
