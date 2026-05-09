# Subagent Prompt Templates

Templates for dispatching agents in the CCF pipeline. Paste full task text — never make subagents read plan files.

## Forge (Implementer)

```
Agent({
  description: "Implement Task N: [task name]",
  subagent_type: "claude-code-flow:forge",
  model: "sonnet",
  prompt: """
## Task Description

[FULL TEXT of task from plan — paste it here]

## Context

[Where this fits, dependencies, architectural context, completed prior tasks]

## Your Job

1. Implement exactly what the task specifies
2. Write tests (TDD: write failing test → implement → verify pass)
3. Commit your work
4. Self-review before reporting

Work from: [directory]

**While you work:** If you encounter something unexpected or unclear, report NEEDS_CONTEXT. Don't guess.

## Self-Review Checklist

- Did I fully implement everything in the spec?
- Did I avoid overbuilding (YAGNI)?
- Did I follow existing patterns in the codebase?
- Do tests verify behavior (not just mock behavior)?

## FILES_MODIFIED (required on completion)
List ALL files created or modified.

## Completion Schema

- **Status:** DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Files modified:
- Verification (commands run + results):
- RED/GREEN evidence:
- Concerns:
"""
})
```

## Sentinel Stage 1 (Spec Compliance)

```
Agent({
  description: "Spec compliance review for Task N",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
Review whether implementation matches specification. READ-ONLY — do not modify any files.

## What Was Requested

[FULL TEXT of task requirements]

## What Was Implemented

[From forge's report — but DO NOT trust it. Verify independently by reading actual code.]

## Your Job

Read the actual code and verify:

**Missing:** Did they implement everything requested? Any skipped requirements?
**Extra:** Did they build things not requested? Over-engineer?
**Misunderstandings:** Different interpretation of requirements?

**Verify by reading code, not by trusting the report.**

Report:
- ✅ Spec compliant
- ❌ Issues found: [list with file:line references]
"""
})
```

## Sentinel Stage 2 (Code Quality)

Only dispatch AFTER Stage 1 passes.

```
Agent({
  description: "Code quality review for Task N",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
Code quality review. READ-ONLY — do not modify any files.

## Scope

BASE_SHA: [commit before task]
HEAD_SHA: [current commit]

## Review Focus

- Does each file have one clear responsibility?
- Are units decomposed for independent understanding and testing?
- Are names clear and accurate?
- Any code smells, security issues, or performance concerns?

## Report Format

- **Strengths:** What's done well
- **Issues:** Critical / Important / Minor (with file:line)
- **Assessment:** Approved | Needs fixes
"""
})
```

## Prism (Testing / Acceptance)

```
Agent({
  description: "Acceptance testing for Task N",
  subagent_type: "claude-code-flow:prism",
  model: "sonnet",
  prompt: """
## Task

[FULL TEXT of acceptance criteria from plan]

## Forge's Report

[From implementer's FILES_MODIFIED and verification output]

## Your Job

1. Read the plan requirements and forge's changes
2. Run the specified test commands
3. Verify behavior matches acceptance criteria
4. Run broader regression if applicable

## Report

- **Status:** ACCEPT | REJECT
- Tests run and results:
- Behavioral verification:
- Concerns:
"""
})
```

## Scout (Research)

Dispatch scout FIRST. Oracle MUST NOT start until scout completes.

```
Agent({
  description: "Research: [topic]",
  subagent_type: "claude-code-flow:scout",
  model: "haiku",
  prompt: """
Research [topic] and produce a structured report.

## Phase 1: Local Codebase Analysis

1. Explore the existing code in [relevant paths] for related patterns, utilities, and conventions
2. Identify existing abstractions that should be reused
3. Note any constraints or gotchas in the current architecture

## Phase 2: External Research

1. [specific external question — APIs, libraries, best practices, etc.]
2. [specific external question]
3. [specific external question]

Use the web-search skill (Tavily) for external research — NOT the built-in WebSearch tool.

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/research-[topic].md`]

Format: concise, actionable, with sources. Structure as:
- **Local findings**: patterns, existing code, constraints
- **External findings**: tools, APIs, best practices, with source URLs
- **Recommendations**: what oracle should consider when planning
"""
})
```

## Scout (UI Research — frontend-UI tasks only)

Use this template INSTEAD of the general scout template when Gate 5 (UI Research) is checked.
If both Gate 2 and Gate 5 are checked, use this template and append any Gate 2-specific research questions (e.g., which state management library to use) to Phase 2.
Dispatch BEFORE Gate 6 (UI Design). UI Design MUST NOT start until this scout completes.

```
Agent({
  description: "UI Research: [product/domain]",
  subagent_type: "claude-code-flow:scout",
  model: "haiku",
  prompt: """
Produce a UI research report for [product/domain].

## Phase 1: Local Codebase Analysis

1. Explore existing UI components, styling patterns, design tokens, theme configuration
2. Identify component library (if any), CSS framework, icon system
3. Note existing color palette, typography choices, spacing conventions
4. Check for existing DESIGN.md — summarize its current tokens and patterns

## Phase 2: Competitor Analysis

Research 2-3 competing/similar products in this domain:
1. Identify their visual language: color palette, typography, iconography style
2. Note distinctive UI patterns and interaction conventions
3. What makes each recognizable (not generic)?
4. Detailed descriptions of key screens (landing, dashboard, settings), with screenshots if tooling supports

Use the web-search skill (Tavily) for competitor research — NOT the built-in WebSearch tool.

## Phase 3: Current Design Aesthetics

Research contemporary design trends relevant to this product domain:
1. Trending visual styles (e.g., bento grids, glassmorphism, brutalist, neo-brutalist, warm minimalism)
2. Typography trends: popular font pairings, variable font usage, size scales
3. Color palette trends: gradient usage, pastel vs saturated, dark mode patterns
4. Interaction patterns: micro-animations, scroll behaviors, transitions
5. What distinguishes current-year design from generic "modern and clean"?

Use the web-search skill (Tavily) for design trend research.

## Output

Save findings to: [output path, e.g. `.claude/flow/designs/ui-research.md`]

Format: concise, visual, with source URLs and screenshots where possible. Structure as:
- **Local findings**: existing design system, tokens, component inventory
- **Competitor analysis**: per-product breakdown with visual language notes
- **Design trends**: actionable aesthetics relevant to this product domain
- **Recommendations**: specific design directions for ui-design skill to consider
"""
})
```
