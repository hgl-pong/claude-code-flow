# Auto-Mode State Machine Reference

## Canonical Phase Enum

The pipeline progresses through these phases in order:

| Phase | Display Alias | Description |
|-------|---------------|-------------|
| `scope` | Scope | Determine research angles |
| `research` | Research | Parallel research per angle |
| `synthesize_spec` | Synthesize Spec | Write spec to `.claude/specs/` |
| `review_spec` | Review Spec | Adversarial spec review |
| `write_plan` | Write Plan | Decompose spec into tasks |
| `review_plan` | Review Plan | Verify plan completeness |
| `parse_plan` | Parse Plan | Extract structured tasks from plan |
| `execute` | Execute | Implement, spec review, code review per task |
| `gates` | Gates | 7 completion gates |
| `finalize` | Finalize | Merge, cleanup |

In `state.json`, the legacy `phase` field uses the user-facing names from the brainstorming/writing-plans/workflow-driven-development/completion-gates/finishing pipeline. The `current_phase` field uses the canonical enum above when running via `full-auto-pipeline.workflow.js`.

## Canonical Status Values

### Terminal Statuses

These statuses indicate the pipeline has stopped and will not continue without external action.

| Status | Meaning | Resume Action |
|--------|---------|---------------|
| `DONE` | Pipeline complete, all gates passed | Print summary. Nothing to do. |
| `STOPPED_ASK_USER` | Pipeline stopped to ask user a question | Do NOT auto-resume. Print the stored question (`stopped_question`) and wait. When user answers, update status and resume from where it stopped. |
| `FAILED_FATAL` | Unrecoverable error | Print error details. User must investigate. |
| `CANCELLED` | User cancelled the run | Nothing to do. |

### Nonterminal Statuses

These statuses indicate the pipeline is mid-flight and may be resumed.

| Status | Meaning | Resume Action |
|--------|---------|---------------|
| `ACTIVE` | Pipeline is actively running | Check `current_phase` and `current_step` to determine what is in progress. |
| `PAUSED_COMPACTING` | Pipeline paused during context compaction | Resume from `current_phase` and `current_step`. |
| `BLOCKED_ESCALATING` | A task is blocked and the escalation ladder is being climbed | Check `task_states` for which task is blocked and which escalation rung was reached. |

### Legacy Statuses (state.json backward compat)

| Status | Meaning | Resume Action |
|--------|---------|---------------|
| `DECIDING` | In a decision loop (clarifying, approaches, design) | Read `current_step`, `clarifications.md`, and `decisions.md`. Skip decisions already logged. Resume from the step indicated by `current_step`. |
| `AWAITING_SUBAGENT` | (DEPRECATED) Dispatched single subagent, waiting for reply | (1) Run `git log --oneline -3` for the task's expected commit. If found, advance task state. (2) If not found, re-dispatch with same prompt, mark `redispatched: true`. |
| `AWAITING_SUBAGENTS` | Multiple subagents dispatched, waiting for any to return | Enumerate `active_agents` array. For each, check `git log --oneline -3` for expected commit. Found agents: advance their `task_states` entry, remove from `active_agents`. Not found: re-dispatch, increment `attempts`. |
| `AWAITING_SHELL` | Running a shell command | Read `last_command`. If idempotent: re-run. If state-mutating: check whether intended state already exists. If already done: skip. If not: re-run. |
| `EXECUTING_GATE` | Running completion gate checks | Read `gate_states`. Resume from the first gate where `passed` is `false`. Do NOT re-check passed gates. |
| `FINISHING` | In finishing phase (merge) | Re-check git state, continue merge. |

## `state.json` Schema v1

```json
{
  "schema_version": 1,
  "task_name": "<sanitized task name slug>",
  "phase": "<brainstorming|writing-plans|workflow-driven-development|completion-gates|finishing>",
  "status": "<TERMINAL or NONTERMINAL status value>",
  "status_detail": {
    "agent_id": "<subagent id, if AWAITING_SUBAGENT (legacy)>",
    "agent_name": "<implementer-task-N (legacy, deprecated)>",
    "task_id": "<plan task id>",
    "dispatched_at": "<ISO timestamp>",
    "redispatched": false,
    "active_count": 0,
    "completed_count": 0
  },
  "current_phase": "<canonical phase enum value from above>",
  "current_step": "<legal current_step value>",
  "progress": {
    "phase_order": ["scope", "research", "synthesize_spec", "review_spec", "write_plan", "review_plan", "parse_plan", "execute", "gates", "finalize"],
    "completed": [],
    "current": "scope",
    "pending": ["research", "synthesize_spec", "review_spec", "write_plan", "review_plan", "parse_plan", "execute", "gates", "finalize"],
    "tasks_total": 0,
    "tasks_completed": 0,
    "tasks_reviewed": 0
  },
  "active_agents": [
    {
      "agent_id": "<subagent id>",
      "task_id": "<plan task id>",
      "role": "implementer|spec-reviewer|code-reviewer",
      "dispatched_at": "<ISO timestamp>"
    }
  ],
  "task_states": {
    "task-1": {
      "status": "<queued|implementing|implemented|spec_reviewing|code_reviewing|passed|blocked|stalled|failed_review|failed|split>",
      "agent_id": "<or null>",
      "attempts": 0,
      "risk": "<low|medium|high|critical>",
      "subsystem": "<string>",
      "runtime_evidence_required": "<required|optional|not_needed>"
    }
  },
  "max_parallel_agents": 5,
  "spec_path": ".claude/specs/<spec-file>",
  "plan_path": ".claude/plans/<plan-file>",
  "decision_trail": ".claude/auto/<task-name>/decisions.md",
  "worktree_path": "<path, if applicable>",
  "stopped_question": null,
  "last_command": null,
  "gate_states": {
    "tasks_executed": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "reviews_passed": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "tests_pass": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "runtime_evidence": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "spec_verified": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "final_review": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" },
    "git_clean": { "passed": false, "iterations": 0, "detail": "", "last_failure": null, "next_action": "retry" }
  },
  "reviewer_loop_iterations": {},
  "updated_at": "<ISO timestamp>"
}
```

## Resume Cursor Fields

The resume cursor is returned by `full-auto-pipeline.workflow.js` and enables mid-pipeline resumption:

```json
{
  "resume_cursor": {
    "phase": "<canonical phase where execution stopped>",
    "phase_index": 0,
    "gate_cursor": 0,
    "gate_states": { "<gate_name>": { "passed": true } },
    "spec_path": "<path or null>",
    "plan_path": "<path or null>",
    "result_replay": ["task-1", "task-2"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `phase` | string | Canonical phase name where execution stopped |
| `phase_index` | number | Index in `PHASE_ORDER` for fast skip comparison |
| `gate_cursor` | number | Number of gates that passed (0-7). Gates below this cursor are skipped on resume. |
| `gate_states` | object | Map of gate name to `{passed: bool}` for already-passed gates |
| `spec_path` | string or null | Path to synthesized spec, for skipping research phases |
| `plan_path` | string or null | Path to written plan, for skipping synthesis phases |
| `result_replay` | string[] | Task IDs that already passed in prior run, for skipping re-execution |

## Task State Fields

Each entry in `task_states`:

| Field | Values | Description |
|-------|--------|-------------|
| `status` | `queued`, `implementing`, `implemented`, `spec_reviewing`, `code_reviewing`, `passed`, `blocked`, `stalled`, `failed_review`, `failed`, `split` | Current status of this task in the pipeline |
| `agent_id` | string or null | ID of the agent currently handling this task |
| `attempts` | number | Number of dispatch attempts for this task |
| `risk` | `low`, `medium`, `high`, `critical` | Task risk level (defaults to `medium`) |
| `subsystem` | string | Subsystem tag (defaults to `unknown`) |
| `runtime_evidence_required` | `required`, `optional`, `not_needed` | Whether runtime evidence gate applies (defaults to `optional`) |

## Gate State Fields

Each entry in `gate_states` uses the canonical gate names (not numbered):

| Gate Name | Check |
|-----------|-------|
| `tasks_executed` | All tasks completed with zero blocked |
| `reviews_passed` | Spec review and code review passed for every task |
| `tests_pass` | Project test suite passes with zero failures |
| `runtime_evidence` | Runtime smoke test passed for runnable deliverables; manifest generated |
| `spec_verified` | Implementation verified against spec line by line |
| `final_review` | Cross-task final review returned approved |
| `git_clean` | Working tree is clean (`git status --porcelain` empty) |

Each gate record:

| Field | Type | Description |
|-------|------|-------------|
| `passed` | boolean | Whether the gate passed |
| `iterations` | number | Number of retry iterations |
| `detail` | string | Human-readable status |
| `last_failure` | string or null | Reason for last failure |
| `last_fix` | string or null | Description of last fix applied |
| `evidence_paths` | string[] | Paths to evidence artifacts |
| `updated_at` | string (ISO 8601) | Timestamp of last update |
| `next_action` | string | Suggested next action (`proceed`, `retry`, or gate-specific action) |
| `fix_applied` | string | Description of fix applied during retry |
| `manifest` | object | (Gate 4 only) Runtime evidence manifest |

## Runtime Evidence Manifest (Gate 4)

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

## Git State Fields

The state file does not store git state directly. Instead:
- `gate_states.git_clean.passed` reflects whether the working tree was clean at last check
- Resume logic checks `git log --oneline -3` to detect commits made by subagents that completed before session ended
- Resume logic checks `git status --porcelain` before re-running destructive commands

## `current_step` Legal Values

| Phase | `current_step` value |
|---|---|
| brainstorming | `explore-context` |
| brainstorming | `offer-visual-companion` |
| brainstorming | `clarifying-questions` |
| brainstorming | `dispatch-researcher` |
| brainstorming | `dispatch-designer` |
| brainstorming | `propose-approaches` |
| brainstorming | `present-design` |
| brainstorming | `write-spec` |
| brainstorming | `spec-review-loop` |
| writing-plans | `scope-check` |
| writing-plans | `technical-research` |
| writing-plans | `write-plan` |
| writing-plans | `plan-review-loop` |
| workflow-driven-development | `dispatch-implementer` |
| workflow-driven-development | `dispatch-parallel` |
| workflow-driven-development | `spec-review-loop` |
| workflow-driven-development | `code-review-loop` |
| completion-gates | `running-gates` |
| finishing | `merging` |

## Write Timing for `state.json`

Update `state.json` BEFORE every state transition. Key moments:
- After creating audit directory: write initial state
- Before dispatching subagent (single): set `AWAITING_SUBAGENT` (legacy)
- Before dispatching parallel subagents: set `AWAITING_SUBAGENTS`, populate `active_agents`, update `task_states`
- After each subagent completes: remove from `active_agents`, update `task_states` entry
- Before running shell command: set `AWAITING_SHELL` + `last_command`
- Before entering a decision: set `DECIDING` + `current_step`
- Between pipeline phases: update `phase`, `progress`, `current_phase`
- When stopped to ask user: set `STOPPED_ASK_USER` + `stopped_question`
- After each completion gate: update `gate_states`, increment `gate_cursor`
- Via flow-state helper: every `flowState('update', ...)` call writes state atomically

## State Writer Handoff

When running via `full-auto-pipeline.workflow.js`, state is written through the `flowState` helper which delegates to `flow-state.py`:

```
flowState(cmd, payload) → workflow({ scriptPath: flowStateScriptPath }, { command, state_file, payload_json, expected_revision })
```

- `cmd='event'` — record a phase or audit event
- `cmd='update'` — write a state update with revision tracking
- The helper uses optimistic concurrency via `expected_revision` to prevent lost updates
- If `flow_state_script_path` is not provided, the helper is a no-op (`{ ok: true }`)

## One Active Run Per Worktree

Only one auto-mode run may be active in a given worktree at a time. The state file path (`.claude/auto/<task-name>/state.json`) is unique per task name per worktree. If a state file exists with a non-terminal status, a new `/auto` invocation must warn and offer to resume or cancel.

## Resume Flow

When resuming (`/auto --resume` or `CCF_AUTO_MODE=1` on startup):

1. Read `.claude/auto/<task-name>/state.json`
2. Read `status`
3. Switch on status (see Status Values tables above)
4. Set `current_phase` to the canonical phase from `state.json`. Set `current_step` to the stored value if valid for that phase. If invalid or missing, use the first step of that phase.
5. If `resume_cursor` exists, use `gate_cursor` to skip already-passed gates and `result_replay` to skip already-passed tasks.
6. Update `state.json` BEFORE every subsequent state change

If `.claude/auto/*/state.json` files exist but no specific task was specified: Glob, sort by `updated_at`, pick most recent. Print: "Resuming auto-mode task `<name>` from `<timestamp>`. Use `/auto --new <task>` to start fresh, `/auto --resume <task-name>` to resume a different one, or `/auto --list` to see all."

## What NOT to Do on Resume

- Do NOT blindly "continue working" without reading state
- Do NOT assume subagent results when session ended mid-wait
- Do NOT re-run destructive commands without checking if they already succeeded
- Do NOT skip phases because "we probably already did that"
- Do NOT re-check gates that are already passed according to `gate_cursor`
