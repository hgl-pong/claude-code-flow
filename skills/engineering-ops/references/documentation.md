# Technical Documentation

## Document Types

### README

```markdown
# Project Name
> One-line description of what this is and why it exists.

## Quick Start
Setup and first run in under 5 minutes. No background reading required.

## Configuration
All env vars, config files, and flags with defaults and allowed values.

## Contributing
Branch naming, PR process, test requirements, and where to ask questions.
```

### API Documentation

````markdown
## Endpoint: [METHOD] /path

**Auth**: Required | None | [specific scheme]
**Rate limit**: N requests/minute

### Request
| Field | Type | Required | Description |
|-------|------|----------|-------------|

### Response (200)
| Field | Type | Description |
|-------|------|-------------|

### Errors
| Code | When | Fix |
|------|------|-----|

### SDK Example
    ```python
    # Minimal working example
    ```
````

### Runbook

```markdown
# [Alert/Scenario Name]

## When to Use
Trigger conditions and symptoms.

## Prerequisites
Access, tools, and permissions needed.

## Steps
1. Verify the symptom: [command]
2. Check [system]: [command]
3. If [condition], do [action]
4. Confirm resolution: [command]

## Rollback
How to undo if the fix makes things worse.

## Escalation
Who to contact and what to include in the escalation.
```

### Architecture Doc

```markdown
## Context
Business problem, constraints, and requirements driving this design.

## Design
System diagram and component responsibilities.

## Decisions
| Decision | Options Considered | Why This One |
|----------|--------------------|--------------|

## Data Flow
How data moves through the system, from entry to persistence.

## Integrations
External systems, contracts, and failure modes.
```

### Onboarding Guide

```markdown
## Setup
Environment, access requests, and first task.

## Key Systems
What each system does and where its code lives.

## Common Tasks
Step-by-step for the 5 things a new person does most often.

## People
Who to ask for what. Prefer roles over names (names change).
```

## Writing Principles

1. **Reader-first** -- Write for the person who knows least about this topic, not for yourself.
2. **Start with the most useful** -- Put "how do I run this" before "why does this exist." The why can come after.
3. **Show, don't tell** -- Commands, code examples, and screenshots beat paragraphs of explanation.
4. **Keep current** -- Stale docs are worse than no docs. Date the doc, own the update, delete what's obsolete.
5. **Link, don't duplicate** -- One source of truth. Link to other docs rather than restating their content.

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_context` to trace code structure and dependencies before writing architecture docs
- Use `gitnexus_query` to find all callers of an API endpoint when writing API docs

## Tips

- Write the README first, then expand into specialized docs. A good README eliminates 80% of questions.
- Every runbook should be testable -- can someone follow it without asking you a question? If not, add the missing step.
- Review docs the same way you review code. Typos in docs become wrong assumptions in production.
