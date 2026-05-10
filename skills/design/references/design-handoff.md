# Design Handoff

Translate a visual design into an engineering-ready specification. The goal: a developer can implement the design without guessing, asking questions, or making visual decisions.

## Specification Sections

### Visual Specifications
- Measurements: exact pixel values, percentages, or relative units
- Design tokens: reference semantic token names, not raw hex or pixel values
- Breakpoints: layout changes at each viewport width with specific values

### Interaction Specifications
- Click and tap targets: what happens, where, and how
- Hover states: visual change, timing, easing
- Transitions: duration, easing curve, which properties animate
- Gestures: swipe, drag, pinch (mobile-specific)

### Content Specifications
- Character limits and truncation rules (ellipsis, wrap, clamp)
- Content states: empty, single item, many items, overflow
- Dynamic content behavior: long names, variable image ratios

### Edge Cases
- Minimum and maximum content lengths
- Internationalization: text expansion (German +30%, Arabic RTL)
- Slow connections: skeleton screens, progressive loading
- Missing data: broken images, empty fields, null states

### Accessibility
- Focus order: tab sequence through interactive elements
- ARIA roles and labels for custom components
- Keyboard navigation: shortcuts, traps, skip links

## Principles

- **Don't assume** — If the design doesn't show it, call it out as unspecified
- **Use tokens, not values** — `interaction-primary` not `#2563EB`
- **Show all states** — Default, hover, focus, active, disabled, loading, error, empty
- **Describe the why** — "16px gap to separate form groups visually" not "gap: 16px"

## Structured Output

```markdown
## Design Handoff: [Component/Page Name]

### Overview
- Purpose: [what this achieves for the user]
- Reference: [screenshot, Figma link, or description]

### Layout
- Grid: [columns, gutter, max-width]
- Breakpoints: [mobile/tablet/desktop specifications]
- Spacing rhythm: [section gap pattern]

### Design Tokens Used

| Token | Value | Applied To |
|-------|-------|------------|
| surface-canvas | #F9F7F4 | Page background |
| text-heading | #0F1011 | Headlines |
| ... | ... | ... |

### Components

| Component | Token Reference | Notes |
|-----------|----------------|-------|
| Primary Button | {interaction-primary} | See states below |
| ... | ... | ... |

### States and Interactions

| State | Visual Change | Transition |
|-------|---------------|------------|
| default | [resting state] | — |
| hover | [change description] | transition-fast |
| focus-visible | [focus ring spec] | transition-fast |
| active | [pressed state] | transition-fast |
| disabled | opacity 0.5, cursor not-allowed | — |
| loading | [skeleton or spinner] | transition-base |
| error | [error indicator] | transition-fast |

### Responsive Behavior

| Breakpoint | Layout Change | Components Affected |
|------------|---------------|-------------------|
| < 640px | [change] | [list] |
| 640-1024px | [change] | [list] |
| > 1024px | [change] | [list] |

### Edge Cases
- Long text: [truncation rule]
- No data: [empty state]
- Slow load: [skeleton behavior]
- RTL: [mirror adjustments]

### Animation/Motion

| Element | Trigger | Duration | Easing |
|---------|---------|----------|--------|
| ... | ... | ... | ... |

### Accessibility Notes
- Focus order: [sequence]
- ARIA: [roles and labels needed]
- Keyboard: [navigation pattern]
- Screen reader: [announcements expected]
```

## If Connectors Available

If **~~image-gen** is connected:
- Use `img describe` to extract layout measurements, color values, and typography from screenshots
- Generate annotated screenshots highlighting token boundaries and state differences

## Tips

- Pair the handoff with a DESIGN.md if the project has one — reference its tokens directly.
- Mark anything unspecified as "NEEDS DESIGN DECISION" rather than guessing.
- Include a screenshot or Figma frame reference at the top for visual context.
