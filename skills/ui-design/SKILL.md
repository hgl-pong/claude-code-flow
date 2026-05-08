---
name: UI Design
version: "1.0.0"
description: "Use for: UI/UX design specs, component design, color/typography systems, design tokens. Produces DESIGN.md for forge to implement."
---

# UI Design

Produces structured, implementable design documents with a strong point of view. Writes `.claude/flow/DESIGN.md` as forge's primary input.

## Iron Law

```
A design without states, breakpoints, accessibility notes, and implementable tokens is not ready for forge.
```

## When to Use This Skill

Oracle decides during planning. This skill is mandatory when:
- Task domain is frontend-UI AND mode is standard+
- Task creates new UI components, pages, or layouts
- Task changes visual design, color system, or typography

This skill is optional when:
- Task is a minor UI tweak (text change, small style fix)
- Task is purely backend with no user-facing output
- Mode is quick (skip unless explicitly requested)

## Behavioral Guards

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The layout is standard, I don't need a reference" | Standard = generic. Pick a reference, borrow AND diverge. |
| "The design tokens are obvious" | Obvious tokens are AI-default tokens. Name them semantically. |
| "I'll just use the default font stack" | Default font stack = every other AI design. Pick deliberately. |
| "The developer can figure out the responsive behavior" | If they could, they wouldn't need a design spec. Specify every breakpoint. |
| "Empty states are low priority" | Empty states are first impressions. Write them first, not last. |

### Red Flags — STOP if you catch yourself thinking:
- "Modern and clean" (banned phrase — be specific)
- "I'll use Inter, it's safe" (safe = invisible)
- "The accent can be blue" (why? what does blue communicate HERE?)
- "I'll skip the loading state spec"
- "This component is simple enough without states"

If product intent, target user, or required flows are unclear, ask for context instead of producing a generic design.

## Process

### Phase 1: Understand Context
Read existing codebase (framework, component library, styling). Read `ui-research.md` if available. Identify domain, users, emotional tone.

### Phase 2: Load Design Knowledge (MANDATORY)
Read at the start of every task:
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/anti-ai-design.md` — anti-AI-generic rules
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-knowledge-base.md` — product references

You must know and follow every rule in anti-ai-design.md. Violations produce AI-generic output.

### Phase 3: Write Real Content First (MANDATORY)
Before layout, write ACTUAL content: real headlines (not "Welcome to our platform"), real numbers, real labels/errors/empty states/edge cases. Content shapes layout. Lorem ipsum = AI-generated.

### Phase 4: Define Design Direction (MANDATORY)
**Mood & Tone**: Pick ONE clear aesthetic. Specific like "warm editorial, serif headings, generous whitespace" or "dense data terminal, monospace accents, dark surfaces".

Banned: "modern and clean", "sleek", "minimal", "intuitive", "user-friendly", anything applicable to any product.

**Design Reference**: From design-knowledge-base.md, select 1-3 products. State borrow AND divergence.

**The One Thing**: What makes this design UNFORGETTABLE? One sentence.

### Phase 5: Produce Design Document

## Failure Modes

- **Generic design**: Passes the "any other product?" test → Fix: add domain-specific personality
- **Missing states**: Only happy path specified → Fix: every component gets all states (empty + loading mandatory)
- **Untitled colors**: `#3b82f6` without semantic name → Fix: `interaction-focus`, `surface-canvas`
- **Copy-paste reference**: Borrowing without diverging → Fix: explicit divergence points required
- **No microcopy**: "Item 1", "Lorem ipsum" → Fix: write real copy before layout

## Output

**Design Brief** (`.claude/flow/DESIGN.md`): Structured markdown — Components table, Design Direction, Color Tokens (semantic + CSS vars), Typography (fonts with rationale, px/rem scale, weights, line-height, letter-spacing), Responsive breakpoints, States per Component. Factual, no prose. This is forge's primary input.

## Self-Review

- [ ] Real content — no lorem ipsum, no "Item 1"
- [ ] Design Direction passes "any other product?" sniff test
- [ ] "The One Thing" written
- [ ] References with explicit borrow AND divergence
- [ ] Every component has ALL states (empty + loading mandatory)
- [ ] Semantic color tokens, tinted grays
- [ ] Typography: specific px/rem with line-height and letter-spacing
- [ ] No banned elements (anti-ai-design.md) without justification
- [ ] Varied layout sections
- [ ] Microcopy for: empty, error, loading, success, onboarding
