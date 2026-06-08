---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

Writing skills = TDD for process docs. Pressure-test agent behavior first, then write the smallest SKILL.md that changes that behavior.

**Core law:** no new or edited skill without a failing pressure test first. If you edited before testing, revert/delete and start over.

## What Skills Are

Reusable technique/pattern/reference guides. Not one-off narratives, project conventions, or mechanical constraints better enforced by hooks/tests.

Personal skill dirs: Claude Code `~/.claude/skills`; Codex `~/.agents/skills/`.

## RED → GREEN → REFACTOR

| Phase | Skill work |
|---|---|
| RED | Run pressure scenario without the skill; record exact failure/rationalization. |
| GREEN | Write minimal docs that address observed failures only. |
| REFACTOR | Re-test; add counters for new loopholes; repeat until behavior holds. |

Testing styles:
- Discipline skills: 3+ combined pressures; success = follows rule under pressure.
- Technique skills: application/variation/missing-info scenarios; success = applies correctly.
- Pattern skills: recognition/application/counter-example scenarios; success = knows when/how.
- Reference skills: retrieval/application/gap tests; success = finds and uses info.

## SKILL.md Contract

```markdown
---
name: skill-name
description: Use when [specific triggers/symptoms only]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.
## When to Use
Symptoms/use cases; not-use cases.
## Pattern / Quick Reference
Steps/table.
## Implementation
Inline small examples or link heavy reference/tool.
## Common Mistakes
Failure → fix.
```

Frontmatter: `name` + `description` required; `name` letters/numbers/hyphens only; frontmatter ≤1024 chars; description third-person, starts `Use when`, describes triggers only, never workflow summary.

## Claude Search Optimization

Description answers: “Should I load this skill now?” Include concrete triggers/symptoms/errors/tools. Avoid process summaries: Claude may follow description shortcut instead of reading body.

Examples:
```yaml
# bad: workflow summary
description: Use for TDD - write test first, implement, refactor
# good: trigger only
description: Use when implementing any feature or bugfix, before writing implementation code
```

Keywords: error strings, symptoms, synonyms, tools. Name by action/core insight: `condition-based-waiting`, `creating-skills`.

## Token Efficiency / Progressive Disclosure

For official authoring details use `anthropic-best-practices.md`. For pressure-test methodology use `testing-skills-with-subagents.md`. For persuasion/rationalization background use `persuasion-principles.md`.

Target frequent skills <200 words, others <500 when possible. Keep layer 1 in SKILL.md: trigger, core rule, shortest safe workflow. Move layer 2/3 detail to references/tools when it is not needed on every load.

Use:
- Cross-references by skill name: `**REQUIRED BACKGROUND:** claude-code-flow:test-driven-development`.
- Tool `--help` instead of flag dumps.
- One strong example, not many mediocre variants.
- No `@file` links unless intentional force-load.

## Flowcharts / Examples / Files

Use flowcharts only for non-obvious decisions or loops. Use tables/lists for reference and numbered lists for linear steps.

One excellent, runnable example beats multi-language samples.

Structure:
```
skills/name/SKILL.md              # required
skills/name/reference.md          # heavy docs only
skills/name/tool.*                # reusable utility only
```

## Rationalization Guards

| Excuse | Reality |
|---|---|
| “Obviously clear” | Clear to you ≠ clear to agents. Test it. |
| “Just docs/reference” | References have gaps. Test retrieval/application. |
| “No time” | Untested skills waste more time later. |
| “Academic review enough” | Reading ≠ using. Run scenarios. |
| “Simple edit” | Edits can weaken triggers. Test before deploy. |

Discipline skills need explicit loophole closure: no “spirit vs letter”, no keeping invalid work “as reference”, no “this case is different”. Add a red-flag list from real baseline failures.

## Checklist

Create todos for these when writing/editing a skill:

1. RED: write scenarios; run without skill; record failures/rationalizations.
2. GREEN: validate name/frontmatter/description; write minimal overview/pattern/reference; include keywords; address RED failures; test with skill.
3. REFACTOR: capture new loopholes; add counters/tables/red flags if needed; re-test.
4. Quality: no narrative; no duplicated workflow; supporting files only for heavy refs/tools; concise progressive disclosure.
5. Deploy: commit/push if configured; consider PR only if broadly useful.
