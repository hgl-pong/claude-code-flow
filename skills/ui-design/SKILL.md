---
name: UI Design
version: "2.1.0"
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
| Spacing scale (space-1 through space-7 with rhythm pattern) | Service boundary definitions |
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
- Task has only incidental frontend changes
- Mode is quick (skip unless explicitly requested)

This skill is skipped when:
- Task is purely backend with no user-facing output

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
- "I'll use a 12-column grid" (default grid = default layout)
- "No blue or purple family primary" without domain-specific justification for why that family communicates the right thing for THIS product

If product intent, target user, or required flows are unclear, ask for context instead of producing a generic design.

## Process

Follow these phases IN ORDER. Each phase builds on the previous one. Do not skip or reorder.

### Phase 1: Load Design Knowledge (MANDATORY — do this FIRST)

Read ALL of these before making ANY design decisions:
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/anti-ai-design.md` — anti-AI-generic rules (MUST follow every rule)
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-knowledge-base.md` — product references with concrete values
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-md-spec.md` — DESIGN.md format spec (Google open standard)
- `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/layout-patterns.md` — layout composition patterns

Violating anti-ai-design.md rules produces AI-generic output. Read them first.

Also read: existing codebase (framework, component library, styling). Read `ui-research.md` if available. Identify domain, users, emotional tone.

**CRITICAL**: Your output is a VISUAL design system. You are NOT writing architecture, data models, API contracts, or system design. If you find yourself describing backend logic, database schemas, or module boundaries, STOP — that belongs in `plan-brief.md`.

### Phase 2: Write Real Content First (MANDATORY)

Before choosing colors, fonts, or layout — write ACTUAL content: real headlines (not "Welcome to our platform"), real numbers, real labels/errors/empty states/edge cases. Content shapes layout. Lorem ipsum = AI-generated.

Write microcopy for these surfaces BEFORE designing their containers:
- Page title and subtitle
- Navigation labels
- Empty state headline + description + CTA text
- Error message text
- Loading state text
- Button labels (primary, secondary, destructive)
- Form field labels and helper text

### Phase 3: Define Emotional Signature

Before choosing visual elements, answer these three questions IN WRITING:

1. **What feeling should the user have after 3 seconds?** (not "professional" — try "I trust this with my money" or "I want to explore more")
2. **What existing product already makes users feel this way?** (name 1-3, from design-knowledge-base.md or beyond)
3. **What is the ONE visual element that will be memorable?** (not "the color" — try "the 72px serif headline against a near-black surface" or "the hand-drawn illustration in the empty state")

**Design Direction**: Pick ONE clear aesthetic. Specific like "warm editorial, serif headings, generous whitespace" or "dense data terminal, monospace accents, dark surfaces". From design-knowledge-base.md, select 1-3 reference products. State what you borrow AND what you deliberately diverge from.

Banned: "modern and clean", "sleek", "minimal", "intuitive", "user-friendly", anything applicable to any product.

Write these into `## Overview` of DESIGN.md.

**Revisit Phase 2 microcopy**: Adjust tone and word choice to match the emotional signature above.

### Phase 4: Build the Design System

#### Step A: Color System

Do NOT start by picking hex values. Start by defining color ROLES, then assign values:

**Required roles** (every design needs these):
| Role | Purpose | Example |
|------|---------|---------|
| `surface-canvas` | Page background — sets temperature | Warm off-white `#F9F7F4` or cool dark `#0E1117` |
| `surface-raised` | Cards, containers — one step up from canvas | White `#FFFFFF` or dark raised `#1A1D23` |
| `text-heading` | Primary content — highest contrast | Near-black `#0F1011` or pure white `#FFFFFF` |
| `text-body` | Secondary content — readable but not shouting | Dark gray `#3D4147` or light gray `#B0B3B8` |
| `text-muted` | Timestamps, metadata — visible but ignorable | Mid gray `#7A8089` or warm gray `#8A8580` |
| `interaction-primary` | Primary CTA, links — the ONE interactive color | Domain-specific, NOT default blue |
| `interaction-hover` | Hover state of primary — predictable shift | 10-15% darker/lighter than primary |
| `interaction-focus` | Focus ring only — visible, not decorative | High contrast, passes 3:1 against surface |
| `status-error` | Errors — unambiguous red-family | `#DC2626` warm red or `#EF4444` |
| `status-success` | Success — unambiguous green-family | `#16A34A` or `#059669` |
| `border-default` | Default borders — barely there | 8-12% opacity of text color on surface |

**Color construction rules**:
- Choose a TEMPERATURE first: warm (add 4-8% red/yellow to grays) or cool (add 4-8% blue/green to grays). Mixed temperature = confused design.
- The `interaction-primary` color must be chosen by DOMAIN: financial/legal → deep teal or navy; creative/artistic → warm amber or terracotta; developer/technical → electric green or cold cyan; health/wellness → sage green or warm coral
- No blue-family or purple-family primary without domain-specific written justification for why that family communicates the right thing for THIS product. `#3B82F6` and `#6366F1` are always banned.
- Test: put your 5 most-used colors in a row. If they could belong to any product, start over.

**Accessibility contrast requirements**:
- `text-heading` on `surface-canvas`: must pass WCAG AA (4.5:1 for normal text, 3:1 for large text)
- `text-body` on `surface-canvas`: must pass WCAG AA (4.5:1)
- `interaction-primary`: must pass 3:1 against adjacent colors (WCAG 1.4.11 non-text contrast)
- All text/background pairs must meet minimum AA — verify with a contrast checker

#### Step B: Type System

Do NOT use the default staircase (`48/36/24/20px`). Build a scale with personality.

**Choose a ratio** (not all scales are equal):
| Ratio | Effect | Products that use it |
|-------|--------|---------------------|
| 1.125 (Major Second) | Tight, dense, information-heavy | Linear, Raycast |
| 1.200 (Minor Third) | Balanced, professional | Vercel, Stripe |
| 1.250 (Major Third) | Expressive, editorial | Apple, Notion |
| 1.333 (Perfect Fourth) | Dramatic, high contrast | Craft Docs |
| 1.414 (√2) | Aggressive contrast | Portfolio sites |

**Font pairing rules**:
- Pick ONE font with character for headings. It must NOT be Inter, Roboto, or system-ui.
- Pick ONE font for body that PAIRS (not matches): serif heading + sans body, or geometric heading + humanist body
- If using variable fonts, define the exact weight axis values (not "medium" — write `fontWeight: 520`)
- Every size must include `lineHeight` and `letterSpacing` — missing values = missing design

**Required type tokens**:
```yaml
typography:
  display:        # Hero headlines — 1-2 per page, extreme scale
  h1:             # Page titles
  h2:             # Section titles
  h3:             # Subsection
  body-lg:        # Lead paragraph, intro text
  body-md:        # Default body
  body-sm:        # Secondary text, descriptions
  caption:        # Timestamps, metadata
  label:          # Form labels, nav items — often uppercase or tracking
  code:           # Monospace for data, terminals
```

#### Step C: Icon System

Define an icon system before components reference icons:
- **Style family**: Pick ONE — outlined, filled, duotone, or two-tone. Do NOT mix styles.
- **Size scale**: `sm: 16px`, `md: 20px`, `lg: 24px` — important actions get larger icons, decorative icons get smaller
- **Stroke width**: Consistent across all icons (1.5px, 2px, or match the type weight)
- **Usage rule**: Icons communicate, never decorate. If removing an icon doesn't reduce understanding, remove it.

Include icon tokens in the YAML frontmatter under a top-level `icons` key. In the markdown body, place icon system as a subsection of `## Typography`.

#### Step D: Spacing Rhythm

Do NOT use the default `4/8/16/24/48px` without reasoning. Build a rhythm:

**Choose a base unit**:
- `4px` base → tight, dense (Linear, Raycast)
- `6px` base → moderate (most products)
- `8px` base → generous, airy (Notion, Apple)

**Required spacing tokens and their purpose**:
| Token | Purpose | Typical range |
|-------|---------|---------------|
| `space-1` | Inline gaps (icon + text) | 4-8px |
| `space-2` | Tight component padding | 8-12px |
| `space-3` | Default component padding | 12-16px |
| `space-4` | Between related elements | 16-24px |
| `space-5` | Between sections | 24-40px |
| `space-6` | Major section breaks | 40-64px |
| `space-7` | Page-level breathing room | 64-96px |

**Rhythm rule**: Sections MUST NOT have identical padding. Create a pattern like `space-5 → space-6 → space-4 → space-7` — this creates visual rhythm. `space-5 → space-5 → space-5` is repetition, not design.

#### Step E: Layout Grid

Do NOT default to "12-column grid". Choose based on content:

| Content type | Grid | Why |
|-------------|------|-----|
| Dashboard / data | 12-col, tight gutters (16-20px) | Maximum layout flexibility |
| Editorial / content | 8-col, generous gutters (24-32px) | Reading comfort |
| Landing / marketing | 6-col or asymmetric split | Dramatic composition |
| Mobile-first | 4-col, 16px gutters | Thumb-friendly |

**Max-width rules**:
- Content-heavy: `720px` (optimal reading width)
- Dashboard: `1200px` (fit multi-column data)
- Full-bleed marketing: `1440px` or fluid

**Breakpoint specification** (REQUIRED for every design):
```
mobile:  < 640px  → <columns>, <gutter>px, <padding>px
tablet:  640-1024px → <columns>, <gutter>px, <padding>px
desktop: > 1024px  → <columns>, <gutter>px, <padding>px, max-width <N>px
```

#### Step F: Elevation Strategy

Pick ONE elevation system and use it consistently:

| System | How it works | Best for |
|--------|-------------|----------|
| Shadow tiers | `sm / md / lg` shadow tokens | General purpose, component-heavy UIs |
| Border-only | No shadows, borders for separation | Flat, editorial, content-first |
| Surface color | Different bg colors for depth | Dark themes, minimal UIs |
| Mixed | Shadow + border + color | Complex dashboards |

**Rules**:
- NEVER use both shadow AND border on the same element (pick one)
- Shadow direction must be consistent (default: `0 1px 3px` downward)
- Z-index layers must be documented: `base(0) → raised(10) → sticky(20) → overlay(30) → modal(40) → tooltip(50)`

#### Step G: Border Radius Scale

Define when each radius level applies. Do NOT use one radius everywhere:

| Token | Use for | Typical range |
|-------|---------|---------------|
| `rounded-sm` | Inputs, tags, badges | 4-6px |
| `rounded-md` | Buttons, cards | 8-10px |
| `rounded-lg` | Modals, panels | 12-16px |
| `rounded-full` | Pills, avatars | 9999px |

**Rule**: Larger containers get larger radii. Smaller interactive elements get smaller radii. Inconsistent radius = intentional; uniform radius = template.

#### Step H: Transition Tokens

Define animation timing so all components animate consistently:

| Token | Duration | Use for |
|-------|----------|---------|
| `transition-fast` | 100-150ms | Hover, focus ring, color shift |
| `transition-base` | 200-300ms | Expand, collapse, layout shift |
| `transition-slow` | 300-500ms | Modal enter, page transition |

**Easing**: Define ONE primary cubic-bezier and document it. Example: `cubic-bezier(0.16, 1, 0.3, 1)` for deceleration.

**Reduced motion**: All transitions must become instant when `prefers-reduced-motion: reduce` is active. Document this in Do's and Don'ts.

#### Step I: Component States

Every component MUST specify these states:
- `default` — resting state
- `hover` — mouse over (predictable change, 10-15% shift)
- `focus-visible` — keyboard focus (2-3px ring, passes contrast check)
- `active` — mouse down (slightly more than hover)
- `disabled` — clearly not interactive (opacity 0.4-0.5, `cursor: not-allowed`, `aria-disabled="true"`)
- `loading` — skeleton or spinner with loading text
- `error` — clearly wrong (red border + error message below, not just color change)

**State transition rule**: Every state change must be SPECIFIC with transition token. "Darker" is not a spec — `backgroundColor: "{colors.primary}" → "darken({colors.primary}, 12%)"` with `transition-fast` is a spec.

**Required component types** (design all that are in scope):
| Component | Minimum required states |
|-----------|----------------------|
| Button (primary) | default, hover, focus-visible, active, disabled, loading |
| Button (secondary) | default, hover, focus-visible, active, disabled |
| Input field | default, focus, error, disabled, with-helper, with-icon |
| Select / Dropdown | default, open, selected, hover-option |
| Card | default, hover (if clickable), loading (skeleton) |
| Navigation item | default, hover, active/current, disabled |
| Toast / Notification | info, success, warning, error |
| Modal / Dialog | backdrop, container, close action |
| Empty state | illustration area, headline, description, CTA |
| Loading state | skeleton layout OR spinner with progress text |

### Phase 5: Layout Composition (for page-level designs)

For any design that spans a full page or major screen, produce a layout composition plan:

1. **Identify the F-pattern or Z-pattern flow** — where does the eye go first?
2. **Define section rhythm** — not identical blocks. Alternate: dense → sparse → dense, or text-heavy → visual → text-heavy. Consult layout-patterns.md for rhythm patterns (Alternating Density, Color Break, Scale Contrast).
3. **Specify the signature moment** — ONE element per page that breaks the pattern intentionally (asymmetric placement, oversized type, full-bleed image, unexpected color block)
4. **Responsive behavior** — what collapses, what reorders, what disappears at each breakpoint

### Phase 6: Produce DESIGN.md

Check if `DESIGN.md` exists in the project root:
- **Exists** → Read it fully, then extend: add new tokens to YAML frontmatter, add new component sections, update Do's and Don'ts. Never overwrite existing tokens.
- **Does not exist** → Create `DESIGN.md` at project root following the full spec in `design-md-spec.md`.

Write YAML frontmatter first (machine-readable tokens), then the 8 markdown body sections in spec order: Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts.

Derive Do's and Don'ts from the Behavioral Guards in this skill and your specific design decisions. Every Don't should reference a concrete anti-pattern (from Red Flags or anti-ai-design.md). Every Do should reference a rule you followed.

Every component in scope for the current task must appear in `## Components` with ALL states specified (default, hover, focus-visible, active, disabled, loading, error). Missing states are a failure.

## Failure Modes

- **Generic design**: Passes the "any other product?" test → Fix: add domain-specific personality
- **Missing states**: Only happy path specified → Fix: every component gets all states (empty + loading mandatory)
- **Untitled colors**: `#3b82f6` without semantic name → Fix: `interaction-focus`, `surface-canvas`
- **Copy-paste reference**: Borrowing without diverging → Fix: explicit divergence points required
- **No microcopy**: "Item 1", "Lorem ipsum" → Fix: write real copy before layout
- **Default spacing rhythm**: Equal padding everywhere → Fix: create deliberate rhythm pattern
- **Missing layout composition**: Just listing components without spatial relationships → Fix: specify section flow, signature moment, responsive collapse
- **No elevation strategy**: Random shadows and borders → Fix: pick one system, document layers
- **Missing contrast check**: Text fails WCAG AA → Fix: verify every text/background pair
- **Missing transitions**: State changes with no timing → Fix: define transition tokens, apply to all states

## Output

**`DESIGN.md`** (project root, alongside `package.json`/`README.md`): Persistent design system document following the [google-labs-code/design.md](https://github.com/google-labs-code/design.md) open standard.

- **YAML frontmatter**: machine-readable tokens — `colors`, `typography`, `icons`, `rounded`, `spacing`, `transitions`, `components` (with `{token.path}` cross-references)
- **Markdown body** (8 sections in spec order): Overview → Colors → Typography → Layout → Elevation & Depth → Shapes → Components → Do's and Don'ts

This is a **persistent project artifact**, not a per-task brief. Forge reads it as the implementation contract. Future UI tasks extend it — never recreate it from scratch.

See `${CLAUDE_PLUGIN_ROOT}/skills/ui-design/references/design-md-spec.md` for full format, schema, and examples.

## Self-Review

- [ ] NO architecture content — zero mentions of API endpoints, data models, system modules, auth flows, or code structure
- [ ] Emotional Signature answers written (3-second feeling, reference products, one memorable element)
- [ ] Design Direction passes "any other product?" sniff test — specific enough to distinguish from competitors
- [ ] "The One Thing" written
- [ ] References with explicit borrow AND divergence
- [ ] Color roles defined before hex values assigned
- [ ] No AI-default colors (`#3B82F6`, `#6366F1`, pure neutral grays)
- [ ] No blue/purple family primary without domain-specific justification
- [ ] All text/background color pairs pass WCAG AA contrast (4.5:1 normal, 3:1 large)
- [ ] Type scale uses a deliberate ratio, NOT the default staircase
- [ ] Font pairing is NOT Inter + Roboto or system-ui stack
- [ ] Every type token has `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`
- [ ] Icon system defined: one style family, size scale, stroke width
- [ ] Spacing rhythm has deliberate variation, NOT equal padding
- [ ] Layout grid chosen based on content type, NOT defaulted to 12-col
- [ ] Elevation strategy picked and documented with z-index layers
- [ ] Border radius scale with different values for different container sizes
- [ ] Transition tokens defined (fast/base/slow) with easing curve
- [ ] Reduced-motion behavior documented
- [ ] YAML frontmatter present with all token groups (colors, typography, icons, rounded, spacing, transitions, components)
- [ ] All color tokens are semantic names, not raw hex in component rules
- [ ] Token cross-references use `{path.to.token}` syntax
- [ ] All 8 markdown body sections present in spec order
- [ ] Real content — no lorem ipsum, no "Item 1"
- [ ] Microcopy for: empty, error, loading, success, onboarding
- [ ] Every in-scope component has ALL states: default, hover, focus-visible, active, disabled, loading, error (empty + success where applicable)
- [ ] Each state change specifies which transition token to use
- [ ] Layout composition plan with section rhythm and signature moment (for page-level designs)
- [ ] Responsive breakpoints with specific column/gutter/padding values
- [ ] No banned elements (anti-ai-design.md) without justification
- [ ] Disabled states include `cursor: not-allowed` and `aria-disabled` (not just visual dimming)
