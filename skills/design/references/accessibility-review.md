# Accessibility Review

Systematic WCAG 2.1 AA audit covering perceivable, operable, understandable, and robust criteria. Produces a prioritized fix list.

## WCAG 2.1 AA Quick Reference

### Perceivable
| Criterion | Requirement |
|-----------|-------------|
| 1.1.1 Non-text Content | All images have meaningful alt text; decorative images use alt="" |
| 1.3.1 Info and Relationships | Semantic HTML structure; headings, lists, tables used correctly |
| 1.4.3 Contrast (Minimum) | Text: 4.5:1 ratio; Large text (18px+ bold / 24px+): 3:1 ratio |
| 1.4.11 Non-text Contrast | UI components and graphics: 3:1 against adjacent colors |

### Operable
| Criterion | Requirement |
|-----------|-------------|
| 2.1.1 Keyboard | All functionality operable via keyboard |
| 2.4.3 Focus Order | Logical tab sequence follows visual layout |
| 2.4.7 Focus Visible | Keyboard focus indicator clearly visible (3:1 contrast) |
| 2.5.5 Target Size | Touch targets minimum 44x44px |

### Understandable
| Criterion | Requirement |
|-----------|-------------|
| 3.2.1 On Focus | No context change on focus alone |
| 3.3.1 Error Identification | Errors identified, described, and suggested to user |
| 3.3.2 Labels or Instructions | Labels provided for all user input |

### Robust
| Criterion | Requirement |
|-----------|-------------|
| 4.1.2 Name, Role, Value | All UI components have accessible name, role, and value |

## Common Issues Checklist

1. **Insufficient contrast** — Text/background fails 4.5:1 (or 3:1 for large text)
2. **Missing form labels** — Inputs without associated label elements or aria-label
3. **No keyboard access** — Interactive elements unreachable via Tab/Enter
4. **Missing alt text** — Images without alt attribute or aria-label
5. **Focus traps** — Modal dialogs that trap focus incorrectly or lack return focus
6. **Missing landmarks** — No main, nav, banner, contentinfo regions
7. **Autoplay media** — Audio/video playing without user control
8. **Time limits** — Auto-redirects or timeouts without warning or extension option

## Testing Approach

| Method | Coverage | When |
|--------|----------|------|
| Automated scan (axe, Lighthouse) | ~30% of issues | First pass, every page |
| Keyboard-only navigation | Operability | Every interactive flow |
| Screen reader (VoiceOver/NVDA) | Semantic structure | Complex components, forms |
| Color contrast check | Perceivable | Every text/background pair |
| 200% zoom test | Responsive + readable | Every page layout |

## Structured Output

```markdown
## Accessibility Review: [Page/Component]

### Summary
- Total issues: [count]
- Critical: [count] | Moderate: [count] | Minor: [count]
- WCAG level achieved: [A / AA / AAA / Fail]

### Perceivable

| Criterion | Finding | Severity | Recommendation |
|-----------|---------|----------|----------------|
| 1.4.3 | Button text contrast 2.8:1 | Critical | Increase to 4.5:1 minimum |

### Operable

| Criterion | Finding | Severity | Recommendation |
|-----------|---------|----------|----------------|
| 2.1.1 | Dropdown not keyboard-openable | Critical | Add Enter/Space key handlers |

### Understandable

| Criterion | Finding | Severity | Recommendation |
|-----------|---------|----------|----------------|
| 3.3.1 | Form error shown only by color | Moderate | Add text description + aria-describedby |

### Robust

| Criterion | Finding | Severity | Recommendation |
|-----------|---------|----------|----------------|
| 4.1.2 | Custom toggle missing role="switch" | Critical | Add role and aria-checked |

### Color Contrast

| Element | Foreground | Background | Ratio | Pass/Fail |
|---------|-----------|------------|-------|-----------|
| Body text | #3D4147 | #F9F7F4 | 7.2:1 | Pass |
| ... | ... | ... | ... | ... |

### Keyboard Navigation

| Element | Reachable | Operable | Focus Visible | Notes |
|---------|-----------|----------|---------------|-------|
| ... | Yes/No | Yes/No | Yes/No | ... |

### Screen Reader

| Component | Name | Role | Value | State | Notes |
|-----------|------|------|-------|-------|-------|
| ... | ... | ... | ... | ... |

### Priority Fixes

| # | Issue | Impact | Effort | Criterion |
|---|-------|--------|--------|-----------|
| 1 | [Most critical fix] | High | Low | 1.4.3 |
| 2 | [Next priority] | High | Medium | 2.1.1 |
| 3 | [Next priority] | Medium | Low | 3.3.1 |
```

## If Connectors Available

If **~~image-gen** is connected:
- Use `img describe` to analyze screenshots for contrast, text readability, and layout issues
- Generate annotated screenshots highlighting accessibility violations with callouts

## Tips

- Start with automated tools (axe, Lighthouse) to catch the easy 30%, then manually test keyboard and screen reader paths.
- Test with actual keyboard navigation — Tab through the entire page. If you get stuck, that is a focus trap.
- Check at 200% zoom: if the layout breaks, content overlaps, or text truncates, it fails responsive accessibility.
