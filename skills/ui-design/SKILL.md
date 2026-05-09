---
name: UI Design
version: "1.0.0"
description: "Use for: UI/UX design specs, component design, color/typography systems, design tokens. Produces DESIGN.md for forge to implement."
---

# UI Design

Produces a persistent `DESIGN.md` design system document (project root) following the Google open standard. Forge reads it as the implementation contract.

## Iron Law

```
A design without states, breakpoints, accessibility notes, and implementable tokens is not ready for forge.
```

## DESIGN.md Is NOT Architecture

This skill produces a **visual design system document** — colors, typography, spacing, component states, visual hierarchy. It is the counterpart to an architect's blueprint: the interior designer's material palette, not the structural engineer's load calculation.

| DESIGN.md IS (this skill) | DESIGN.md IS NOT (do not write) |
|---|---|
| Color tokens with hex values | API endpoint contracts |
| Typography scale (font, size, weight, line-height) | Data model schemas |
| Component states (hover, focus, disabled, loading) | Module dependency diagrams |
| Spacing scale (xs/sm/md/lg/xl) | Service boundary definitions |
| Border-radius and elevation tokens | Database table designs |
| Responsive breakpoints and grid system | Authentication/authorization flows |
| Visual hierarchy and layout composition | Code architecture decisions |
| Real microcopy (labels, errors, empty states) | Implementation technical strategy |

**If the output contains API routes, data models, system diagrams, or code architecture — it is the WRONG document.** That content belongs in `plan-brief.md` or `phase-context.md` under `## Architecture`.

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

**CRITICAL**: Your output is a VISUAL design system. You are NOT writing architecture, data models, API contracts, or system design. If you find yourself describing backend logic, database schemas, or module boundaries, STOP — that belongs in `plan-brief.md`.

## Phase 2: Load Design Knowledge (MANDATORY)
Read at the start of every task:
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/anti-ai-design.md` — anti-AI-generic rules
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-knowledge-base.md` — product references
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-md-spec.md` — DESIGN.md format spec (Google open standard)

You must know and follow every rule in anti-ai-design.md. Violations produce AI-generic output.

### Phase 3: Write Real Content First (MANDATORY)
Before layout, write ACTUAL content: real headlines (not "Welcome to our platform"), real numbers, real labels/errors/empty states/edge cases. Content shapes layout. Lorem ipsum = AI-generated.

### Phase 4: Define Design Direction (MANDATORY)
**Mood & Tone**: Pick ONE clear aesthetic. Specific like "warm editorial, serif headings, generous whitespace" or "dense data terminal, monospace accents, dark surfaces".

Banned: "modern and clean", "sleek", "minimal", "intuitive", "user-friendly", anything applicable to any product.

**Design Reference**: From design-knowledge-base.md, select 1-3 products. State borrow AND divergence.

**The One Thing**: What makes this design UNFORGETTABLE? One sentence.

### Phase 5: Produce Design Document

Check if `DESIGN.md` exists in the project root:
- **Exists** → Read it fully, then extend: add new tokens to YAML frontmatter, add new component sections, update Do's and Don'ts. Never overwrite existing tokens.
- **Does not exist** → Create `DESIGN.md` at project root following the full spec in `design-md-spec.md`.

Write YAML frontmatter first (machine-readable tokens), then the 8 markdown body sections in spec order: Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts.

Every component in scope for the current task must appear in `## Components` with ALL states specified (default, hover, focus-visible, active, disabled, loading, error). Missing states are a failure.

## Failure Modes

- **Generic design**: Passes the "any other product?" test → Fix: add domain-specific personality
- **Missing states**: Only happy path specified → Fix: every component gets all states (empty + loading mandatory)
- **Untitled colors**: `#3b82f6` without semantic name → Fix: `interaction-focus`, `surface-canvas`
- **Copy-paste reference**: Borrowing without diverging → Fix: explicit divergence points required
- **No microcopy**: "Item 1", "Lorem ipsum" → Fix: write real copy before layout

## Output

**`DESIGN.md`** (project root, alongside `package.json`/`README.md`): Persistent design system document following the [google-labs-code/design.md](https://github.com/google-labs-code/design.md) open standard.

- **YAML frontmatter**: machine-readable tokens — `colors`, `typography`, `rounded`, `spacing`, `components` (with `{token.path}` cross-references)
- **Markdown body** (8 sections in spec order): Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts

This is a **persistent project artifact**, not a per-task brief. Forge reads it as the implementation contract. Future UI tasks extend it — never recreate it from scratch.

See `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-md-spec.md` for full format, schema, and examples.

## Self-Review

- [ ] NO architecture content — zero mentions of API endpoints, data models, system modules, auth flows, or code structure
- [ ] YAML frontmatter present with all token groups (colors, typography, rounded, spacing, components)
- [ ] All color tokens are semantic names, not raw hex in component rules
- [ ] Token cross-references use `{path.to.token}` syntax
- [ ] All 8 markdown body sections present in spec order
- [ ] Real content — no lorem ipsum, no "Item 1"
- [ ] Design Direction passes "any other product?" sniff test
- [ ] "The One Thing" written
- [ ] References with explicit borrow AND divergence
- [ ] Every in-scope component has ALL states (default, hover, focus-visible, active, disabled, loading, error — empty + success where applicable)
- [ ] Typography: specific px values with line-height and letter-spacing
- [ ] No banned elements (anti-ai-design.md) without justification
- [ ] Microcopy for: empty, error, loading, success, onboarding
