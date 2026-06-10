# Auto-Mode Audit Trail Reference

## Directory Structure

```
.claude/auto/<task-name>/
├── state.json           # Current pipeline state — used for interruption recovery
├── decisions.md         # Decision log — one entry per automated choice
├── clarifications.md    # Auto-answered clarifying questions + reasoning
├── approaches.md        # Approach comparison + which was picked + why
├── design-approval.md   # Design sections and auto-approval record
└── plan-checklist.md    # Gate results (all 7 gates) with pass/fail timestamps
```

## File Creation Order

Create `.claude/auto/<task-name>/` directory at pipeline start. Write `state.json` immediately (initial state). Other files are written as the pipeline progresses:

- `clarifications.md` — during brainstorming phase, one entry per inferred answer
- `approaches.md` — after research, before design
- `design-approval.md` — section by section as design is auto-approved
- `decisions.md` — append-only, throughout all phases
- `plan-checklist.md` — during completion gate phase, updated as each gate passes

## Event Schema

When running via `full-auto-pipeline.workflow.js`, the pipeline records structured audit events to the `auditEvents` array (returned in the final result). Each event:

```json
{
  "type": "<event_type>",
  "timestamp": "<ISO 8601>",
  "phase": "<canonical phase enum value>",
  "detail": "<human-readable description>",
  "data": {}
}
```

## Required Event Types

| Event Type | When Emitted | Data Fields |
|------------|-------------|-------------|
| `phase_start` | At the start of each pipeline phase | `phase`: canonical phase name |
| `phase_complete` | When a phase finishes successfully | `phase`, plus phase-specific data (e.g., `spec_path`, `plan_path`) |
| `run_complete` | When the entire pipeline finishes | `status`: terminal status, `gates_passed`: count |
| `stopped_ask_user` | When pipeline stops for user input | `question`: the question asked, `resume_cursor`: current cursor |
| `gate_result` | When a completion gate passes or fails | `gate`: gate name, `passed`: bool, `iterations`: count |
| `task_result` | When a task is classified into a partition | `task_id`, `partition`: partition name, `classification` (if blocked) |
| `escalation` | When a task climbs the escalation ladder | `task_id`, `rung`: escalation stage, `reason` |
| `review_result` | When a spec/code/final review completes | `stage`: review stage, `passed`: bool, `blocking_issues`: count |

### Phase-Specific Update Payloads

| Phase | Update Payload |
|-------|---------------|
| `scope` | `{ phase: 'scope' }` |
| `research` | `{ phase: 'research' }` |
| `synthesize_spec` | `{ phase: 'synthesize_spec', spec_path: '<path>' }` |
| `write_plan` | `{ phase: 'write_plan', plan_path: '<path>' }` |
| `execute` | `{ phase: 'execute', execute_result: <result> }` |
| `gates` | `{ phase: 'gates', gate_cursor: <N>, gate_states: <map> }` |
| `finalize` | `{ phase: 'finalize', status: '<DONE|BLOCKED_ESCALATING>' }` |

## Seven Completion Gates

Gates run in canonical order. Each gate must pass before the next begins.

| # | Gate Name | Predicate | Retry Cap |
|---|-----------|-----------|-----------|
| 1 | `tasks_executed` | All tasks completed, zero blocked | 10 |
| 2 | `reviews_passed` | Spec review + code review passed for every completed task | 5 per issue |
| 3 | `tests_pass` | Project test suite runs with zero failures | 10 |
| 4 | `runtime_evidence` | Runnable deliverables: build/run succeeds, no crash/hang, evidence manifest generated. Non-runnable: auto-pass. | 10 |
| 5 | `spec_verified` | Each requirement in spec verified present in codebase | 10 |
| 6 | `final_review` | Cross-task code review on full diff returns approved | 5 per issue |
| 7 | `git_clean` | Working tree clean (`git status --porcelain` empty) | 10 |

### Gate Record Enrichment

Every gate record includes:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Canonical gate name |
| `passed` | boolean | Whether the gate passed |
| `detail` | string | Human-readable status |
| `iterations` | number | Number of retry attempts |
| `last_failure` | string or null | Reason for most recent failure |
| `last_fix` | string or null | Description of last fix applied |
| `evidence_paths` | string[] | Paths to evidence artifacts |
| `updated_at` | string (ISO 8601) | Timestamp |
| `next_action` | string | `proceed` on pass, gate-specific action on fail |
| `fix_applied` | string | Description of fix during retry |

## Evidence Manifest

Gate 4 (`runtime_evidence`) produces a structured manifest:

```json
{
  "commands": "<commands that were run>",
  "exit_codes": [0],
  "logs": [],
  "screenshots": [],
  "artifacts": [],
  "crash": false,
  "hang": false,
  "unverified_acceptance_items": [],
  "blocking_risks": [],
  "generated_at": "<ISO 8601>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `commands` | string | Commands executed for smoke test |
| `exit_codes` | number[] | Exit codes from each command |
| `logs` | string[] | Relevant log excerpts |
| `screenshots` | string[] | Paths to screenshot evidence |
| `artifacts` | string[] | Paths to other evidence artifacts |
| `crash` | boolean | Whether a crash was detected |
| `hang` | boolean | Whether a hang was detected |
| `unverified_acceptance_items` | string[] | Acceptance items that could not be verified |
| `blocking_risks` | string[] | Risks that block passing (empty on pass) |
| `generated_at` | string (ISO 8601) | When the manifest was generated |

### Task Evidence

Each task that passes produces an evidence record:

```json
{
  "commit_sha": "<git SHA>",
  "test_results": "<test output summary>",
  "verification_commands": ["<commands>"],
  "evidence_paths": ["<paths>"],
  "concerns": ["<concerns from implementer>"],
  "files_modified": ["<paths>"]
}
```

## Result Partitions

Each task appears in exactly one partition: `passed`, `completed`, `blocked`, `stalled`, `failed_review`, or `needs_escalation`. `completed` is a compatibility alias for passed task IDs.

## Escalation Events

When a task is blocked, the pipeline climbs the escalation ladder. Each step is recorded:

```json
{
  "type": "escalation",
  "task_id": "<task id>",
  "rung": "<escalation stage>",
  "attempt": 1,
  "reason": "<why the task is blocked>",
  "classification": "<blocker taxonomy category>"
}
```

### Escalation Ladder

| Stage | Max Attempts | Description |
|-------|-------------|-------------|
| `schema_retry` | 1 | Retry with same prompt, fresh agent |
| `self_service_retry` | 2 | Retry with a self-service prompt providing guidance |
| `stronger_model` | 1 | Retry with a more capable model |
| `split_subtask` | 1 | Split task into smaller sub-tasks |
| `enriched_context` | 1 | Retry with additional context from codebase search |
| `ask_user` | 1 | Escalate to human partner |

### Blocker Taxonomy

Every blocked task is classified into one of these categories:

| Category | Description |
|----------|-------------|
| `agent_output_invalid` | Agent produced malformed or unusable output |
| `merge_conflict` | Unresolvable merge conflict |
| `permissions` | Permission denied on file or resource |
| `external_service` | External service unavailable or errored |
| `tooling_unavailable` | Required tool not installed or not found |
| `test_failure` | Tests fail and cannot be fixed by agent |
| `runtime_failure` | Runtime smoke test fails |
| `dependency_failure` | Dependency installation or resolution failure |
| `architecture_decision` | Blocked on an architectural decision |
| `scope_too_large` | Task is too large for a single agent |
| `missing_context` | Agent lacks necessary context |

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
  - 7/7 completion gates passed
  - 0 user interruptions needed

Review: cat .claude/auto/<task-name>/decisions.md
Revert: git revert <merge-commit>
```
