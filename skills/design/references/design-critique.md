# Design Critique

Provide structured, actionable design feedback across five dimensions. Match depth to the design's stage — early exploration needs direction, final polish needs precision.

## Critique Dimensions

### 1. First Impression (2-Second Test)
What does a user understand in 2 seconds? What is this? What can I do here? If the answer isn't immediate, the design has a hierarchy problem.

### 2. Usability
Can the user accomplish their primary goal without confusion? Check navigation clarity, interactive element discoverability, information flow, and cognitive load.

### 3. Visual Hierarchy
Where does the eye go first, second, third? Does the reading order match task priority? Check emphasis, whitespace rhythm, and typographic contrast.

### 4. Consistency
Does the design follow its own rules? Check design system compliance — spacing, colors, typography, component usage. Inconsistency erodes trust.

### 5. Accessibility
Can everyone use this? Check color contrast (WCAG AA), touch targets (44px minimum), text readability, focus indicators, and meaningful alt text. For a full audit, invoke the accessibility-review mode.

## Feedback Guidelines

- **Be specific** — "The CTA lacks contrast" not "it needs work"
- **Explain why** — "Users won't see this because..." not "this is wrong"
- **Suggest alternatives** — "Try moving X below Y" not "rearrange this"
- **Acknowledge what works** — Lead with strengths, then address issues
- **Match the stage** — Exploration: big-picture direction. Wireframe: structure and flow. High-fidelity: pixel-level details. Final polish: edge cases and states.

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| Critical | Blocks user task or violates accessibility | Must fix before shipping |
| Moderate | Frustrates or confuses users | Should fix, has workaround |
| Minor | Polish opportunity | Nice to have |

## Structured Output

```markdown
## Design Critique

### Overall Impression
[2-3 sentences: first impression, emotional tone, stage-appropriate assessment]

### Usability

| Finding | Severity | Recommendation |
|---------|----------|----------------|
| ... | Critical/Moderate/Minor | ... |

### Visual Hierarchy
- Eye path: [element order]
- Strongest element: [what draws attention first]
- Weakest element: [what gets lost]
- Whitespace assessment: [adequate/tight/wasteful]

### Consistency

| Finding | Severity | Recommendation |
|---------|----------|----------------|
| ... | Critical/Moderate/Minor | ... |

### Accessibility

| Check | Pass/Fail | Notes |
|-------|-----------|-------|
| Color contrast (4.5:1 text) | | |
| Touch targets (44px) | | |
| Text readability | | |
| Focus indicators | | |
| Alt text / labels | | |

### What Works Well
- [Specific strengths worth preserving]

### Priority Recommendations (Top 3)
1. [Most impactful fix]
2. [Second most impactful]
3. [Third most impactful]
```

## If Connectors Available

If **~~image-gen** is connected:
- Use `img describe` to analyze uploaded screenshots for layout, color, and typography details
- Generate annotated comparison images showing before/after for recommendations

## Tips

- Share context: what product, who are the users, what is the primary task? Critique without context is guessing.
- Specify the design stage: exploration needs different feedback than final polish.
- Ask to focus: request critique on a specific dimension when you don't need the full audit.
