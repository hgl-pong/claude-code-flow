---
name: Research
version: "2.0.0"
description: "Dispatch research subagents for technical research, library evaluation, product analysis, competitor analysis, gap analysis, user research, research synthesis, or knowledge synthesis. Also handles planning/conducting user research studies and synthesizing findings into themes and insights."
argument-hint: "<topic to research, or 'user-research'/'synthesis'/'knowledge-synthesis' for specialized modes>"
---

# Research

**IMPORTANT**: Research is a SKILL, NOT an agent. Always dispatch with `subagent_type: "general-purpose"`. NEVER use `subagent_type: "claude-code-flow:research"` — that agent type does not exist and will cause an error.

Research subagents are **general-purpose** agents dispatched with inlined methodology. No dedicated agent needed. Research is read-only — dispatch multiple simultaneously with no conflict.

## Modes

| Mode | Trigger | Reference |
|------|---------|-----------|
| **Technical Research** (default) | Library evaluation, API comparison, best practices | This file + `references/dispatch-templates.md` |
| **User Research** | "user research plan", "interview guide", "usability test", "survey design" | `references/user-research.md` |
| **Research Synthesis** | "synthesize research", "find patterns", "analyze interview data" | `references/research-synthesis.md` |
| **Knowledge Synthesis** | "combine findings", "cross-reference", "merge sources" | `references/knowledge-synthesis.md` |
| **Workflow Intake Research** | External repo/plugin/workflow comparison before changing this workflow | `skills/workflow-intake/SKILL.md` + this file |

Auto-detect mode from context, or default to Technical Research.

## When to Use

- Technical research: library evaluation, API comparison, best practices investigation
- Product analysis: gap analysis, competitor analysis (ULI mode)
- UI research: competitor visual analysis, design intelligence gathering
- User research: planning interviews, designing usability tests, structuring studies
- Research synthesis: distilling transcripts/surveys into themes and recommendations
- Knowledge synthesis: merging multi-source results with dedup and confidence scoring
- Workflow intake: inspect outside workflow systems as evidence for `workflow-intake`, not as content to copy wholesale

**Do NOT use for:** simple lookups that do not require synthesis, debugging (use systematic-debugging skill).

## Iron Law

**NEVER fabricate information. If you cannot find it, say so. Do not guess.**

Source cross-reference: verify claims with 2+ independent sources. Single-source claims must be flagged as "unverified — single source". NEVER write to source code files.

## Process (Technical Research)

### Phase 1: Clarify Scope

1. State the research question explicitly — what decision does this research support?
2. Define "done" — what specific outputs will the consumer (oracle/forge/user) need?
3. Identify constraints — versions, platforms, licensing, bundle size, compatibility requirements

### Phase 2: Local Codebase Analysis

Before looking outward, understand what already exists:

1. **Inventory** — scan relevant directories for existing patterns, utilities, abstractions
2. **Dependencies** — check `package.json`, `Cargo.toml`, `pyproject.toml`, or equivalent for current dependencies
3. **Conventions** — identify coding patterns, naming conventions, error handling style in use
4. **Constraints** — note architectural boundaries, banned patterns, performance requirements
5. **Gaps** — what's missing that the task requires but doesn't exist yet?
6. **Interfaces** — what existing APIs/types/interfaces must the new work conform to?

Deliverable: a "Local Context" section that prevents re-inventing what already exists.

### Phase 3: External Research

1. Formulate targeted search queries (specific, technical, include versions)
2. Cross-reference multiple sources, verify currency (dates, deprecation notices)
3. Prefer official docs, standards, release notes over blog posts
4. For library comparisons: check GitHub stars, last commit date, open issues, breaking changes
5. For API evaluation: check rate limits, pricing, authentication model, SDK maturity
6. For architecture patterns: look for real-world case studies with scale/traffic data

### Phase 4: Synthesis

1. Merge local findings with external findings — where do they align, conflict, or complement?
2. Assign confidence levels using the standard below
3. Produce actionable recommendations with trade-offs explicitly stated
4. Flag open questions that cannot be resolved by research alone

## Confidence Levels

| Level | Criteria | Citation Rule |
|-------|----------|--------------|
| **High** | 2+ authoritative sources agree, published <1yr, confirmed locally | No disclaimer needed |
| **Medium** | 1+ corroborating source, OR authoritative source >1yr old | Flag as "Medium confidence" |
| **Low** | Single source, conflicting sources, OR unable to verify | Flag as "Low confidence — unverified" |
| **Local** | Verified by reading local code directly | Highest confidence for internal questions |

## Process (Workflow Intake Research)

1. Bound the source scope: read overview docs, command/agent/skill manifests, hook/runtime docs, and any policy files.
2. Extract ideas, not files. Group them as agents, skills, commands, hooks, rules, docs, runtime, or tests.
3. For each idea, note fit with this repo's existing lanes and whether it requires a new dependency.
4. Flag duplicated surfaces and project-specific content as rejection candidates.
5. Return findings in an Adopt / Adapt / Reject / Defer table for the `workflow-intake` skill.

## Common Mistakes

| Failure | Fix |
|---------|-----|
| Single-source claims | Cross-reference or flag as unverified |
| Stale information | Check dates, prefer current sources |
| Scope drift | Stay focused on what was asked |
| Unactionable findings | Include versions, APIs, trade-offs |
| Fabricated URLs | Only cite URLs you actually visited |

## Output

Structured research report with these sections:

1. **Research Question** — what was investigated and why
2. **Local Context** — existing code, patterns, dependencies, constraints, gaps
3. **External Findings** — per-finding: topic, result, sources (URLs), confidence level
4. **Comparison** (if evaluating options) — side-by-side with decision criteria
5. **Recommendations** — ranked, with trade-offs and confidence
6. **Open Questions** — what couldn't be determined, what needs prototype/spike
7. **Intake Table** (for workflow intake only) — source idea, target lane, decision, reason

## Dispatching

See `references/dispatch-templates.md` for prompt templates (Technical Research, UI Research, Product Analysis). UI Research and Product Analysis are specialized methodologies with their own phase structures tailored to their domains. All share the Iron Law, confidence levels, and cross-reference requirements. Templates inline these — no need for subagents to read this file.

## Tips

- Start from the question, not the sources. Research answers a question.
- Write research questions BEFORE writing interview questions.
- When confidence is low, say so. Unclear attribution beats false certainty.
