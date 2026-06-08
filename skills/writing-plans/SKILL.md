---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

Create implementation plans detailed enough for an agent with zero project context and mediocre judgment. Include exact files, code, tests, commands, dependencies. DRY, YAGNI, TDD, frequent commits.

Announce: “I'm using the writing-plans skill to create the implementation plan.” Save to `.claude/plans/YYYY-MM-DD-<feature-name>.md` unless user preference overrides.

## Gates Before Planning

- Before writing a plan, an approved spec/design/requirements doc from `claude-code-flow:brainstorming` must exist.
- Plan should follow that approved spec/design/requirements doc.
- If spec spans independent subsystems, split into separate plans first.
- Dispatch technical researcher with `skills/workflow-driven-development/researcher-prompt.md`; save `.claude/research/<task-name>/technical-research.md`.
- Research must cover relevant files/symbols (`file:line`), patterns, impact/risk, test commands, constraints, source provenance (`local`/`web`/`both`).
- If research reveals ambiguity, broad scope, or technical conflict → stop and ask.

## Design Task Shape

Before tasks, map files to create/modify and each responsibility. Prefer focused files and existing patterns. Include targeted splits only when needed for this goal.

Dependencies: each task may include `**Depends on:** Task X`. No line = immediately dispatchable. Only depend on earlier tasks. Independent tasks run concurrently under workflow-driven-development.

Granularity: tasks and steps should be small. Use the exact phrase `2-5 minutes` (ASCII hyphen) when describing timing. Each task should be small / a few minutes of focused work. Each step is one bite-sized 2-5 minutes action: write failing test → run red → implement minimal green → run tests → commit.

## Required Header

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use claude-code-flow:workflow-driven-development (recommended) or claude-code-flow:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [one sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [key tech]
**Spec:** `.claude/specs/YYYY-MM-DD-<feature-name>-design.md`
**Technical research:** `.claude/research/<task-name>/technical-research.md`
---
```

## Task Template

````markdown
### Task N: [Component]

**Depends on:** Task X (omit if none)
**Files:**
- Create: `path/file.py`
- Modify: `path/existing.py:123-145`
- Test: `tests/path/test_file.py`

- [ ] **Step 1: Write failing test**
```python
def test_specific_behavior():
    assert function(input) == expected
```

- [ ] **Step 2: Run RED**
Run: `pytest tests/path/test_file.py::test_specific_behavior -v`
Expected: FAIL because [missing behavior]

- [ ] **Step 3: Minimal implementation**
```python
def function(input):
    return expected
```

- [ ] **Step 4: Run GREEN**
Run: `pytest tests/path/test_file.py::test_specific_behavior -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tests/path/test_file.py path/file.py
git commit -m "feat: add specific behavior"
```
````

## No Placeholders

Never write: TBD/TODO/later; “add appropriate error handling”; “write tests for above”; “similar to Task N”; steps without code/commands; undefined types/functions. Repeat necessary code because tasks may run out of order.

## Plan Review + Handoff

1. Dispatch reviewer with `plan-document-reviewer-prompt.md`, spec, technical research, approved `DESIGN.md` if relevant, and plan.
2. Reviewer checks spec/research coverage, missing steps, placeholders, type/signature consistency, command accuracy, testability, scope creep.
3. Revise/re-review until approved. If blocker/requirement conflict appears, ask user.
4. Save plan and execute. Default: `claude-code-flow:workflow-driven-development`. Inline only when config-only/no logic/no tests/no review need: `claude-code-flow:executing-plans`.

Do not ask user to choose execution mode; announce chosen mode and proceed.
