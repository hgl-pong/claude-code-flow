---
name: Writing Skills
version: "1.1.0"
description: "Use when creating new skills or editing existing skills — quality standard for skill authoring"
---

# Writing Skills

## Overview

Skills are reference guides for proven techniques. They help future sessions find and apply effective approaches.

**Skills are:** Reusable techniques, patterns, tools, reference guides.
**Skills are NOT:** Narratives about how you solved a problem once.

## SKILL.md Structure

```
---
name: Skill-Name-With-Hyphens
version: "1.0.0"
description: "Use when [specific triggering conditions]"
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
Symptoms and use cases. When NOT to use.

## Core Pattern / Process
Steps, flowchart, or pattern description.

## Quick Reference
Table or bullets for scanning.

## Common Mistakes
What goes wrong + fixes.
```

## Naming & Directory

- Name: letters, numbers, hyphens only. Verb-first: `writing-skills` not `skill-creation`
- Directory: `skills/skill-name/SKILL.md` (required) + supporting files (optional)
- Separate files for heavy reference (100+ lines) or reusable tools
- Keep inline: principles, code patterns (<50 lines)

## Token Efficiency

- Frequently-loaded skills: <400 words
- Other skills: <500 words
- Cross-reference instead of repeating
- One excellent example beats many mediocre ones
- Prefer tables over prose for comparisons

## Reference

For CSO rules, discipline kit pattern, cross-referencing conventions, and self-review checklist see `authoring-guide.md` in this directory.
