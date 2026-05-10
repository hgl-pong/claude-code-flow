---
name: Research
version: "2.0.0"
description: "Dispatch research subagents for technical research, library evaluation, product analysis, competitor analysis, gap analysis, user research, research synthesis, or knowledge synthesis. Also handles planning/conducting user research studies and synthesizing findings into themes and insights."
argument-hint: "<topic to research, or 'user-research'/'synthesis'/'knowledge-synthesis' for specialized modes>"
---

# Research

Research subagents are **general-purpose** agents dispatched with inlined methodology. No dedicated agent needed. Research is read-only — dispatch multiple simultaneously with no conflict.

## Modes

| Mode | Trigger | Reference |
|------|---------|-----------|
| **Technical Research** (default) | Library evaluation, API comparison, best practices | This file + `references/dispatch-templates.md` |
| **User Research** | "user research plan", "interview guide", "usability test", "survey design" | `references/user-research.md` |
| **Research Synthesis** | "synthesize research", "find patterns", "analyze interview data" | `references/research-synthesis.md` |
| **Knowledge Synthesis** | "combine findings", "cross-reference", "merge sources" | `references/knowledge-synthesis.md` |

Auto-detect mode from context, or default to Technical Research.

## When to Use

- Technical research: library evaluation, API comparison, best practices investigation
- Product analysis: gap analysis, competitor analysis (ULI mode)
- UI research: competitor visual analysis, design intelligence gathering
- User research: planning interviews, designing usability tests, structuring studies
- Research synthesis: distilling transcripts/surveys into themes and recommendations
- Knowledge synthesis: merging multi-source results with dedup and confidence scoring

**Do NOT use for:** codebase exploration (use gitnexus), simple web lookups (use web-search skill directly), debugging (use systematic-debugging skill).

## Iron Law

**NEVER fabricate information. If you cannot find it, say so. Do not guess.**

Source cross-reference: verify claims with 2+ independent sources. Single-source claims must be flagged as "unverified — single source". NEVER write to source code files.

## Process (Technical Research)

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

See `references/dispatch-templates.md` for prompt templates (Technical Research, UI Research, Product Analysis). UI Research and Product Analysis are specialized variants of Technical Research — they share the same methodology but add domain-specific focus areas. Templates inline the Iron Law and methodology — no need for subagents to read this file.

## If Connectors Available

If **~~code-intel** is connected:
- Cross-reference code search results with documentation

If **~~web-search** is connected:
- Fill gaps in source coverage with supplementary queries

## Tips

- Start from the question, not the sources. Research answers a question.
- Write research questions BEFORE writing interview questions.
- When confidence is low, say so. Unclear attribution beats false certainty.
