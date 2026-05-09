# CSO and Authoring Reference

## CSO (Claude Search Optimization) Rules

The description field decides whether this skill gets loaded. Write it for discovery.

**CRITICAL: Description = When to Use, NOT What the Skill Does.**

```yaml
# BAD: Summarizes workflow
description: Use for TDD — write test first, watch it fail, write minimal code, refactor

# GOOD: Just triggering conditions
description: Use when implementing any feature or bugfix, before writing implementation code
```

**Rules:**
- Start with "Use when..."
- Include specific triggers, symptoms, and situations
- Write in third person
- NEVER summarize the skill's process or workflow in the description
- Keep under 500 characters

**Why:** Descriptions that summarize workflow create shortcuts. Claude follows the description instead of reading the full skill body.

## Discipline Kit Pattern

For skills that enforce discipline (TDD, debugging, verification), include the three-piece kit:

1. **Iron Law** — One-sentence non-negotiable rule, bold, at the top
2. **Rationalization Table** — Excuse vs Reality table
3. **Red Flags** — Bullet list of thoughts that mean STOP

```markdown
## Iron Law

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |

## Red Flags — STOP

- Code before test
- "I'll write tests after"
```

## Cross-Referencing

Reference other skills by name with explicit markers:

- `**REQUIRED SUB-SKILL:** Use testing-strategy` — must understand before using
- `**SUGGESTED:** Use writing-plans` — recommended next step
- Never use `@` links to force-load files (burns context)

## Self-Review Checklist

Before finalizing any skill:

- [ ] YAML frontmatter with `name` and `description`
- [ ] Description starts with "Use when..."
- [ ] Description does NOT summarize workflow
- [ ] Name uses only letters, numbers, hyphens
- [ ] Clear overview with core principle
- [ ] "When to Use" with specific triggers
- [ ] No `TBD`, `TODO`, or placeholder language
- [ ] Discipline skills have Iron Law + Rationalization Table + Red Flags
- [ ] Under 500 words for standard skills, under 400 for frequently-loaded skills
- [ ] Cross-references use REQUIRED/SUGGESTED format
