# Pipeline Operations Reference

Detailed gate specifications, context envelope templates, and scheduling rules for the development pipeline.

## Mandatory Gate Checklist (Full)

```
GATE CHECKLIST (evaluate for this specific task):

[ ] Gate 1: Brainstorm — mandatory for: new features, behavior changes, UI work,
    architecture changes, broad refactors. Skip only for: narrow bug fixes with
    known root cause, config changes, single-file edits with clear spec.

[ ] Gate 2: Research (scout) — see mode table. If mandatory: scout MUST
    complete BOTH local codebase analysis AND external web research before
    plan gate. Scout and oracle are SEQUENTIAL — never dispatch oracle
    until scout finishes and its findings are available.

[ ] Gate 3: Plan (oracle) — ALWAYS mandatory for standard/deep/autonomous.
    Oracle MUST produce `<output_dir>/plan-brief.md` with TaskCreate tasks.
    Oracle MUST receive scout's findings as input when Gate 2 was checked.

[ ] Gate 4: Architecture (oracle) — see mode table. If mandatory: oracle
    MUST produce design document before implementation.

[ ] Gate 5: UI Research (scout) — mandatory when task domain is frontend-UI
    AND mode is standard+. Scout MUST produce ui-research.md covering:
    a) Local codebase: existing components, styling patterns, design tokens.
    b) Competitor analysis: 2-3 similar products in the same domain — UI patterns,
       visual language, interaction conventions.
    c) Current design aesthetics: trending visual styles, typography choices,
       color palettes, and interaction patterns relevant to the product domain.
    Scout MUST complete before Gate 6 (UI Design) starts.

[ ] Gate 6: UI Design (ui-design skill) — mandatory when task domain is frontend-UI
    AND mode is standard+. UI design skill MUST produce DESIGN.md before forge
    can be dispatched for UI work.

[ ] Gate 7: Review (sentinel) — see mode table. If mandatory: sentinel
    MUST approve before acceptance.

[ ] Gate 8: Acceptance (prism) — mandatory for standard/deep/autonomous.
    Prism MUST accept before completion.

EXECUTION RULE: Execute gates in order (1→2→3→4→5→6→7→8), skipping only
unchecked gates. You MAY NOT skip a checked gate. You MAY NOT reorder gates.
```

## Context Envelope Template

Every agent prompt MUST be self-contained. Omitting fields = incomplete dispatch. If a field does not apply, write `N/A - <reason>`.

```markdown
## Envelope
- **Goal:** <one-line project goal>
- **Your Task:** <exact task subject from TaskGet>
- **Working Directory:** `<absolute or project-relative cwd>`
- **Completed Dependencies:** <specific outputs now present in git/filesystem>
- **File Scope:** <exact files to create/modify>
- **Test Command:** `<exact command to run for verification>`
- **Acceptance Criteria:** <from task description>
- **Relevant Excerpts:** <requirements/design/code snippets needed to act without reading a separate plan>
- **Constraints:** <project conventions, banned patterns, dependency limits>
- **Out of Scope:** <nearby work the agent must not touch>

## FILES_MODIFIED (required on completion)
List ALL files you created or modified: <path1>, <path2>, ...
```

For implementation agents, append:

```markdown
## Completion Schema
- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Files modified: <same list as FILES_MODIFIED>
- Verification: `<command>` -> <pass/fail + key output>
- RED/GREEN evidence: <required for behavior changes>
- Concerns: <specific risks, or "none">
```

## Agent Dispatch Call

```
Agent({
  description: "<task_subject>",
  subagent_type: "claude-code-flow:<agent>",
  model: "<agent_model>",
  prompt: "<full context envelope + task details>",
  isolation: "<worktree if conflict detected, else omit>",
  run_in_background: true
})
```

**Dispatch all non-conflicting agents in a single message** (multiple Agent calls).

## Parallel Limits

| Agent Type | Max Parallel | Isolation |
|---|---|---|
| forge (code) | 3 | worktree if file conflict |
| prism (tests) | 2 | worktree if file conflict |
| prism (build) | 1 | never parallel |

## File Conflict Analysis

Before dispatching multiple agents simultaneously:
1. Use `TaskGet` on each candidate task to read its description
2. Extract file paths mentioned in "Files:" section or description text
3. If two tasks share any file path → **conflict detected**
4. Conflicting tasks: dispatch with `isolation: "worktree"` (each gets its own branch)
5. Non-conflicting tasks: dispatch without isolation (share worktree)
6. Prefer one agent per file cluster unless the tasks are clearly disjoint.

## Completion Handling

When an agent completes:
1. Read its output — verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` declaration against task scope
3. Check verification evidence includes command, status, and key output
4. If behavior changed, confirm RED/GREEN evidence or dispatch correction
5. If worktree was used: review changes, merge if clean
6. `TaskUpdate` status=completed only after scope and evidence checks pass
7. Record evidence in `verification-evidence.jsonl`
8. Check if new tasks are now unblocked → dispatch next batch

After every 3 tasks: write key decisions to `<output_dir>/phase-context.md`.

## Error Recovery

```
syntax error     → auto-correct, retry
dependency error → install, retry
logic error      → investigate, fix or escalate
environment error → escalate to user
unknown          → investigate (max 2 retries), escalate
```

## Subagent-Driven Review (deep/autonomous mode)

For deep and autonomous modes, dispatch each review stage as a **separate sentinel subagent** for zero context contamination:

1. Dispatch sentinel with `review_focus: spec_compliance` in the context envelope → spec-only review
2. If APPROVE: dispatch a **fresh** sentinel with `review_focus: code_quality` → quality-only review
3. If Stage 1 REQUEST CHANGES: back to implementer (max 3 rounds)

For quick/standard: single sentinel run with both stages (no `review_focus` parameter) — backward compatible.
