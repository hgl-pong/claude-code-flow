# Auto-Mode Audit Trail Reference

## Directory Structure

```
.claude/auto/<task-name>/
├── state.json           # Current pipeline state — used for interruption recovery
├── decisions.md         # Decision log — one entry per automated choice
├── clarifications.md    # Auto-answered clarifying questions + reasoning
├── approaches.md        # Approach comparison + which was picked + why
├── design-approval.md   # Design sections and auto-approval record
└── plan-checklist.md    # Gate results (all 6 gates) with pass/fail timestamps
```

## File Creation Order

Create `.claude/auto/<task-name>/` directory at pipeline start. Write `state.json` immediately (initial state). Other files are written as the pipeline progresses:

- `clarifications.md` — during brainstorming phase, one entry per inferred answer
- `approaches.md` — after research, before design
- `design-approval.md` — section by section as design is auto-approved
- `decisions.md` — append-only, throughout all phases
- `plan-checklist.md` — during completion gate phase, updated as each gate passes

## `decisions.md` Format

```markdown
## [timestamp] [phase] <decision summary>

**What would have been asked:** <the user gate being bypassed>
**Decision:** <what auto-mode chose>
**Reasoning:** <why — project pattern / community default / YAGNI / etc.>
**Alternatives considered:** <what else was considered, why rejected>
```

## `clarifications.md` Format

```markdown
# Auto-Answered Clarifying Questions

## Clarifying Question 1

**Question auto-mode inferred:** <what was unclear>
**Auto-answer:** <what was assumed>
**Basis:** <project context / file evidence / reasonable default>
**Risk:** LOW | MEDIUM | HIGH — <what could go wrong if this is wrong>
```

## `approaches.md` Format

```markdown
# Approach Selection

## Approach A: <name> (REJECTED)
- **Description:** ...
- **Why rejected:** ...

## Approach B: <name> (SELECTED)
- **Description:** ...
- **Why selected:** ...

## Approach C: <name> (REJECTED)
- **Description:** ...
- **Why rejected:** ...
```

## `design-approval.md` Format

```markdown
# Design Section Auto-Approvals

## Section: <name>
**Status:** APPROVED
**Content:** <summary of what was approved>
**Timestamp:** <ISO timestamp>
```

## Pipeline End Summary

When auto-mode finishes (including successful merge), print:

```
Auto-mode complete. Decision trail at .claude/auto/<task-name>/
  - N clarifying questions auto-answered
  - M approaches evaluated
  - 6/6 completion gates passed
  - 0 user interruptions needed

Review: cat .claude/auto/<task-name>/decisions.md
Revert: git revert <merge-commit>
```
