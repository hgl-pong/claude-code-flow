---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `claude-code-flow:using-git-worktrees` skill at execution time.

**Save plans to:** `.claude/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## Technical Research Gate

Before writing the plan, dispatch a researcher subagent using `skills/workflow-driven-development/researcher-prompt.md` with research type `technical-research`. Researcher saves to:

```text
.claude/research/<task-name>/technical-research.md
```

The researcher uses dual-source tools:
- **Local codebase retrieval:** Glob, Grep, Read, CodeGraph — find relevant files, symbols, patterns, call graphs, impact areas
- **Web search:** WebSearch, WebFetch, web_search_prime, webReader — API docs, changelogs, known issues, best practices, version-specific behavior

Technical research must cover:

- Relevant files and symbols (with file:line references)
- Existing patterns to follow
- Impact/risk areas
- Test commands and acceptance checks
- Constraints that shape task decomposition

Every finding carries source provenance (`local` | `web` | `both`). Conflicts between local code and web docs are flagged with a recommendation.

The plan must cite the technical research path and reflect its conclusions. If research reveals the spec is ambiguous, too broad, or technically inconsistent, stop and ask the user before planning.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Dependencies

Declare `**Depends on:**` in each task header to enable parallel dispatch. When workflow-driven-development executes the plan, tasks with no dependencies run concurrently (Workflow runtime manages parallelism automatically). Tasks wait until all their `depends_on` tasks are `done`.

- If Task B creates a file that Task C imports → Task C depends on Task B
- If tasks touch completely independent files → no dependency needed
- Omit `**Depends on:**` line entirely if no dependencies (task is immediately dispatchable)
- Only depend on earlier task numbers (Task N can only depend on Task < N)

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use claude-code-flow:workflow-driven-development (recommended) or claude-code-flow:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Spec:** `.claude/specs/YYYY-MM-DD-<feature-name>-design.md`

**Technical research:** `.claude/research/<task-name>/technical-research.md`

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Depends on:** Task X, Task Y (omit if none — task is immediately dispatchable)
**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Plan Review Loop

After writing the complete plan, run a reviewer loop before offering execution choices:

1. Dispatch a reviewer with the spec, technical research doc, approved `DESIGN.md` if applicable, and the plan.
2. Reviewer checks spec coverage, research coverage, missing steps, placeholders, type/signature consistency, command accuracy, testability, and scope creep.
3. If the reviewer finds issues, revise the plan and send it back to the same reviewer for re-review.
4. Repeat until approved.
5. If the loop exposes unresolved requirement conflicts or technical blockers, stop and ask the user.

## Execution Handoff

After the plan reviewer approves the plan, save it and execute. Default to workflow-driven — inline is only for trivial tasks.

**Default: Workflow-Driven**
- **REQUIRED SUB-SKILL:** Use claude-code-flow:workflow-driven-development
- Fresh subagent per task + two-stage review

**Inline Execution only when ALL of:**
- Config-only, no new logic or tests
- No review loop needed

If qualifying for inline:
- **REQUIRED SUB-SKILL:** Use claude-code-flow:executing-plans
- Batch execution with checkpoints for review

Do not ask the user to choose. Announce which mode and proceed.
