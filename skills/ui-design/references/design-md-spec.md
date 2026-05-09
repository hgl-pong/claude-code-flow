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
  primary: "#1A1C1E"                # always hex, SRGB
  secondary: "#6C7278"
  tertiary: "#B8422E"
  surface-canvas: "#F9F7F4"
  surface-raised: "#FFFFFF"
  text-heading: "#0F1011"
  text-body: "#3D4147"
  text-muted: "#7A8089"
  interaction-focus: "#2563EB"
  error: "#DC2626"
  success: "#16A34A"
typography:
  h1:
    fontFamily: Public Sans
    fontSize: 48px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.02em
  h2:
    fontFamily: Public Sans
    fontSize: 32px
    fontWeight: 600
    lineHeight: 1.15
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
rounded:
  sm: 4px
  md: 8px
  lg: 16px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface-canvas}"
    rounded: "{rounded.md}"
    padding: "12px 20px"
  input:
    backgroundColor: "{colors.surface-canvas}"
    textColor: "{colors.text-body}"
    rounded: "{rounded.sm}"
---
```

**Rules**:
- Colors must start with `#` (hex SRGB)
- Token references use `{path.to.token}` syntax
- `<scale-level>` keys: `xs`, `sm`, `md`, `lg`, `xl`, `full` (or any descriptive string)
- No duplicate section headings

### Part 2: Markdown Body (8 sections, fixed order)

```markdown
## Overview

[Brand personality, target audience, emotional response the UI should evoke.
Be specific: "warm editorial for independent researchers" not "modern and clean".]

## Colors

[Semantic palette rationale. Why each color, what it communicates.
Include dark-mode variants if applicable.]

## Typography

[Type scale rationale. Hierarchy decisions. Why these fonts for this product.
Include web font import or system-font fallback stack.]

## Layout

[Spacing scale usage. Grid system (columns, gutters, margins).
Responsive breakpoints: mobile (<640px), tablet (640–1024px), desktop (>1024px).
Max content width. Container padding at each breakpoint.]

## Elevation & Depth

[Shadow scale. When to use shadow vs border vs color-only separation.
Z-index layers: base, raised, overlay, modal, tooltip.]

## Shapes

[Border-radius philosophy. When sm/md/lg applies.
Exceptions: inputs use sm, modals use lg, pills use full.]

## Components

[Per-component guidance. Each component MUST specify ALL states:
default, hover, focus-visible, active, disabled, loading, error.
Empty and success states where applicable.]

### Button

States: default / hover / focus-visible / active / disabled / loading
[Describe each state with token references]

### Input Field

States: default / focus / error / disabled
[Helper text, label positioning, character count]

### [Add components as needed for the current task]

## Do's and Don'ts

Do:
- [Specific actionable rules derived from anti-ai-design.md + this product's personality]

Don't:
- [Specific things that would make this look generic or off-brand]
```

---

## Token Reference Syntax

Cross-reference tokens with `{path.to.token}`:

```yaml
components:
  button-primary:
    backgroundColor: "{colors.primary}"      # references colors.primary
    rounded: "{rounded.md}"                  # references rounded.md
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
