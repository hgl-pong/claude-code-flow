# UX Copy

Write interface text that helps users succeed. Every word earns its place.

## Principles

| Principle | Meaning |
|-----------|---------|
| Clear | Users understand on first read |
| Concise | Shortest path to meaning |
| Consistent | Same term for same thing, everywhere |
| Useful | Tells users what to do next |
| Human | Reads like a person wrote it |

## Copy Patterns

### CTAs
- **Verb-first**: "Create project", not "Project creation"
- **Specific outcome**: "Send invoice" not "Submit"
- **Match action**: Button label = what happens next
- Pairs: "Cancel" / "Delete", "Discard" / "Save", "Skip" / "Continue"

### Error Messages
Structure: **What happened** + **Why** + **How to fix**

```
Payment failed. Your card was declined. Try a different payment method or contact your bank.
```

### Empty States
Structure: **What's empty** + **Why it matters** + **How to start**

```
No projects yet. Create your first project to start tracking tasks.
[Create Project]
```

### Confirmation Dialogs
- State the action clearly
- Describe irreversible consequences
- Label buttons with the action, not "Yes/No"

```
Delete "Project Alpha"?
All 47 tasks and 12 files will be permanently removed.
[Cancel]  [Delete Project]
```

### Tooltips
- Concise supplement, not a manual
- Never repeat the label
- Helpful context only

### Loading States
- Set expectations: "Loading dashboard..." not "Loading..."
- Progress when possible: "Uploading 3 of 8 files..."

### Onboarding
- Progressive disclosure: show minimum to start, reveal complexity later
- Action-oriented: "Pick a template to get started" not "Welcome to our platform"

## Voice and Tone

Adapt tone to context, not personality.

| Context | Tone | Example |
|---------|------|---------|
| Success | Celebratory, not over the top | "Published! Your post is live." |
| Error | Empathetic and helpful | "Couldn't save. Check your connection and try again." |
| Warning | Clear and actionable | "Unsaved changes will be lost if you leave." |
| Neutral | Informative and concise | "Last synced 2 minutes ago." |

## Output Template

```markdown
## Recommended Copy
**[Component]**: "[Copy text]"

## Alternatives
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | "[text]" | [tone] | [context] |
| B | "[text]" | [tone] | [context] |

## Rationale
[Why this copy works for the context and audience]

## Localization Notes
- [Potential issues for translation: idioms, length constraints, cultural references]
```

## If Connectors Available

## Tips

- Read copy aloud. If it sounds robotic, rewrite it.
- Audit for jargon. Replace with plain language users actually use.
- Test with the surrounding UI — copy in isolation misleads.
