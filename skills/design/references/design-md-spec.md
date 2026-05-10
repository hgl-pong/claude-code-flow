# DESIGN.md Format Specification

Source: google-labs-code/design.md open standard (https://github.com/google-labs-code/design.md)

DESIGN.md is a **persistent, project-level design system document** — not a per-task brief. Create it once, extend it as new components are needed.

---

## File Location

`DESIGN.md` in the project root (alongside `package.json`, `README.md`, etc.).

If a `DESIGN.md` already exists: read it first, then ADD new sections or tokens for the current task. Never overwrite; always extend.

---

## Structure

Two parts: YAML frontmatter (machine-readable tokens) + markdown body (human-readable rationale).

### Part 1: YAML Frontmatter

```yaml
---
version: alpha
name: <design-system-name>          # e.g. "Daylight Prestige", "Carbon Zero"
description: <optional one-liner>
colors:
  surface-canvas: "#F9F7F4"
  surface-raised: "#FFFFFF"
  text-heading: "#0F1011"
  text-body: "#3D4147"
  text-muted: "#7A8089"
  interaction-primary: "#2563EB"
  interaction-hover: "#1D4ED8"
  interaction-focus: "#2563EB"
  status-error: "#DC2626"
  status-success: "#16A34A"
  border-default: "#E5E7EB"
typography:
  display:
    fontFamily: Public Sans
    fontSize: 64px
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.03em
  h1:
    fontFamily: Public Sans
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
  h2:
    fontFamily: Public Sans
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.015em
  body-md:
    fontFamily: Public Sans
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label-caps:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1
    letterSpacing: 0.1em
  code:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
icons:
  style: outlined
  sizes:
    sm: 16px
    md: 20px
    lg: 24px
  strokeWidth: 1.5px
rounded:
  sm: 4px
  md: 8px
  lg: 16px
  full: 9999px
spacing:
  space-1: 4px
  space-2: 8px
  space-3: 16px
  space-4: 24px
  space-5: 32px
  space-6: 48px
  space-7: 80px
transitions:
  fast: "150ms cubic-bezier(0.16, 1, 0.3, 1)"
  base: "250ms cubic-bezier(0.16, 1, 0.3, 1)"
  slow: "400ms cubic-bezier(0.16, 1, 0.3, 1)"
components:
  button-primary:
    backgroundColor: "{colors.interaction-primary}"
    textColor: "{colors.surface-canvas}"
    rounded: "{rounded.md}"
    padding: "12px 20px"
    transition: "{transitions.fast}"
  button-primary-hover:
    backgroundColor: "{colors.interaction-hover}"
    transition: "{transitions.fast}"
  button-primary-focus:
    boxShadow: "0 0 0 2px {colors.interaction-focus}"
  button-primary-disabled:
    opacity: "0.4"
    cursor: "not-allowed"
  input:
    backgroundColor: "{colors.surface-canvas}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.sm}"
    border: "1px solid {colors.border-default}"
    transition: "{transitions.fast}"
  input-focus:
    borderColor: "{colors.interaction-focus}"
    boxShadow: "0 0 0 2px {colors.interaction-focus}"
---
```

**Rules**:
- Colors must start with `#` (hex SRGB)
- Token references use `{path.to.token}` syntax
- Spacing tokens use `space-N` naming with semantic purpose (space-1 = inline gap, space-7 = page breathing room)
- No duplicate section headings

### Part 2: Markdown Body (9 sections, fixed order)

```markdown
## Visual Theme & Atmosphere

[Brand personality, target audience, emotional response the UI should evoke.
Be specific: "warm editorial for independent researchers" not "modern and clean".
Includes Emotional Signature: 3-second feeling, reference products, the One Thing.]

## Color Palette & Roles

[Semantic palette rationale. Why each color, what it communicates.
Include dark-mode variants if applicable.
Verify all text/background pairs pass WCAG AA (4.5:1).]

## Typography Rules

[Type scale rationale. Hierarchy decisions. Why these fonts for this product.
Include web font import or system-font fallback stack.
Icon system: style family, size scale, stroke width, usage rules.]

## Component Stylings

[Per-component guidance. Each component MUST specify ALL states:
default, hover, focus-visible, active, disabled, loading, error.
Empty and success states where applicable.
State transitions must reference transition tokens.]

### Button

States: default / hover / focus-visible / active / disabled / loading
[Describe each state with token references and transition token]

### Input Field

States: default / focus / error / disabled
[Helper text, label positioning, character count]

### [Add components as needed for the current task]

## Layout Principles

[Spacing scale usage. Grid system (columns, gutters, margins).
Section rhythm pattern. Signature moment for page-level designs.
Max content width. Container padding.]

## Depth & Elevation

[Shadow scale. When to use shadow vs border vs color-only separation.
Z-index layers: base, raised, overlay, modal, tooltip.
Border radius scale: sm/md/lg rules per container type.]

## Do's and Don'ts

Do:
- [Specific actionable rules derived from anti-ai-design.md + this product's personality]

Don't:
- [Specific things that would make this look generic or off-brand]

## Responsive Behavior

[Responsive breakpoints: mobile (<640px), tablet (640–1024px), desktop (>1024px).
Touch targets. Collapsing/reordering strategy.
Layout changes at each breakpoint.]

## Agent Prompt Guide

[Quick color reference table for AI agents.
Ready-to-use prompts for generating components in this design system.
Common token combinations.]
```

---

## Token Reference Syntax

Cross-reference tokens with `{path.to.token}`:

```yaml
components:
  button-primary:
    backgroundColor: "{colors.interaction-primary}"
    rounded: "{rounded.md}"
    transition: "{transitions.fast}"
```

---

## Unknown Content Handling

| Scenario | Behavior |
|----------|----------|
| Unknown section heading (e.g. `## Iconography`) | Preserve — valid extension |
| Unknown token name | Accept if value is valid |
| Duplicate section heading | Error — reject the file |

---

## Extending an Existing DESIGN.md

When a `DESIGN.md` already exists:
1. Read the entire file first
2. Add new tokens to the YAML frontmatter (never remove existing ones)
3. Add new component sections to `## Components`
4. Update `## Do's and Don'ts` if new patterns emerge
5. Never change existing token values unless the user explicitly changed the design direction

---

## Anti-Patterns — What NOT to Write

These sections indicate the file has drifted into architecture documentation, not visual design. If you find yourself writing any of these, STOP and move that content to `plan-brief.md` or `phase-context.md`:

```markdown
## WRONG — Architecture content (do NOT put in DESIGN.md)

### System Architecture
The app follows a microservices pattern with an API gateway...

### Data Model
User { id: string, email: string, role: enum }

### API Endpoints
GET /api/users — returns list of users
POST /api/auth/login — authenticates user

### Authentication Flow
1. User submits credentials
2. Server validates against database
3. JWT token issued

### Module Structure
src/
  auth/
  components/
  services/

### Technical Decisions
We use React Query for server state management...
```

```markdown
## CORRECT — Visual design content (what DESIGN.md should contain)

### Colors
Primary: "#1A1C1E" — near-black authority, grounds the interface
Surface canvas: "#F9F7F4" — warm off-white, no clinical white

### Typography
Display: Public Sans 64px/700, line-height 1.05, letter-spacing -0.03em
Body: Public Sans 16px/400, line-height 1.6
Icons: Outlined, 1.5px stroke, sizes 16/20/24px

### Components — Button Primary
Default: bg {colors.interaction-primary}, text {colors.surface-canvas}, rounded {rounded.md}, transition {transitions.fast}
Hover: bg {colors.interaction-hover}
Focus-visible: 2px ring {colors.interaction-focus}
Disabled: opacity 0.4, cursor not-allowed, aria-disabled true

### Layout
Grid: 8 columns, 24px gutters, max-width 1200px
Mobile (<640px): 4 columns, 16px gutters
Spacing rhythm: space-5 → space-6 → space-4 → space-7
```

**The rule**: If a section would make sense in a backend engineer's planning document, it does NOT belong in DESIGN.md. DESIGN.md is the visual language forge uses to write CSS/components — colors, spacing, typography, component states, responsive behavior, transitions.
