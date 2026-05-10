# Design System Management

Three modes for working with a design system: audit existing consistency, document what exists, or extend with new patterns.

## Modes

### Audit — Consistency Check
Evaluate the design system for gaps, inconsistencies, and coverage.

Checklist:
- **Token coverage**: Are all colors, spacing, typography, and borders tokenized? Any hardcoded values?
- **Naming consistency**: Do token names follow a convention? Any aliases or duplicates?
- **Component completeness**: Does every component specify all states (default, hover, focus, active, disabled, loading, error)?
- **Variant coverage**: Are all needed variants documented, or are some implicit/undocumented?
- **Accessibility coverage**: Do all components have focus, contrast, and ARIA specs?

Output a **System Health Score** (0-100) with breakdown.

### Document — Component Specs
Produce a full component specification for one component or pattern.

Includes: description, variants, props/API, states, accessibility notes, do's and don'ts, code example snippet.

### Extend — New Patterns
Design a new component or pattern that fits the existing system.

Includes: problem statement, analysis of existing patterns, proposed design with token references, accessibility considerations, open questions for review.

## Design System Components

### Design Tokens
Colors (semantic roles), typography (scale + ratio), spacing (base unit + rhythm), borders, shadows (elevation tiers), motion (duration + easing).

### Components
Variants (primary/secondary/ghost), states (default/hover/focus/active/disabled/loading/error), sizes, behavior, accessibility.

### Patterns
Forms, navigation, data display, feedback — reusable interaction patterns.

## Principles

- **Consistency over creativity** — New patterns must feel like they belong
- **Flexibility within constraints** — Tokens allow variation, not chaos
- **Document everything** — Undocumented patterns are invisible patterns
- **Version and migrate** — Track changes, provide upgrade paths

## Structured Output

### Audit Output

```markdown
## Design System Audit

### Overall Score: [0-100]

| Category | Score | Issues |
|----------|-------|--------|
| Token Coverage | /25 | [count] |
| Naming Consistency | /25 | [count] |
| Component Completeness | /25 | [count] |
| Accessibility Coverage | /25 | [count] |

### Token Issues
| Issue | Severity | Location | Fix |
|-------|----------|----------|-----|
| Hardcoded color in button | Critical | button.css:42 | Replace with {interaction-primary} |

### Component Gaps
| Component | Missing States | Missing Variants |
|-----------|---------------|-----------------|
| ... | ... | ... |

### Recommendations (Priority Order)
1. ...
```

### Document Output

```markdown
## Component: [Name]

### Description
[One sentence: what it does and when to use it]

### Variants
| Variant | Use Case | Visual Difference |
|---------|----------|-------------------|
| ... | ... | ... |

### Props / API
`[prop: type = default — description]`

### States
| State | Visual | Transition | Accessibility |
|-------|--------|------------|---------------|
| default | ... | — | ... |
| hover | ... | transition-fast | ... |
| focus-visible | ... | transition-fast | 2-3px ring, 3:1 contrast |
| disabled | ... | — | aria-disabled, cursor not-allowed |
| loading | ... | transition-base | aria-busy, live region |
| error | ... | transition-fast | aria-invalid, error message |

### Do's and Don'ts
- Do: [specific correct usage]
- Don't: [specific incorrect usage]

### Code Example
[Framework-appropriate snippet using design tokens]
```

### Extend Output

```markdown
## Proposed: [Pattern Name]

### Problem
[What user or developer need this addresses]

### Existing Patterns Analyzed
| Pattern | Similarity | Why It Doesn't Fit |
|---------|-----------|-------------------|
| ... | ... | ... |

### Proposed Design
- Tokens used: [list with references to existing tokens]
- Variants: [list]
- States: [all states specified]

### Accessibility
- Focus behavior: ...
- ARIA requirements: ...
- Keyboard interaction: ...

### Open Questions
1. [Decision needed before implementation]
```

## If Connectors Available

If **~~code-intel** is connected:
- Run `gitnexus_query` to find all component usage across the codebase
- Run `gitnexus_impact` before renaming or restructuring tokens to assess blast radius

## Tips

- Start with audit mode to understand the current state before documenting or extending.
- When extending, always check if an existing pattern covers 80% of the need — prefer composition over new components.
- Run audit after extending to verify the new pattern maintains system consistency.
