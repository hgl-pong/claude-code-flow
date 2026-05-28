# Auto-Mode State Machine Reference

## `state.json` Schema

```json
{
  "task_name": "<sanitized task name slug>",
  "phase": "<brainstorming|writing-plans|subagent-driven-development|completion-gates|finishing>",
  "status": "<DECIDING|AWAITING_SUBAGENT|AWAITING_SUBAGENTS|AWAITING_SHELL|EXECUTING_GATE|STOPPED_ASK_USER|FINISHING|DONE>",
  "status_detail": {
    "agent_id": "<subagent id, if AWAITING_SUBAGENT (legacy, single-agent)>",
    "agent_name": "<implementer-task-N (legacy, deprecated)>",
    "task_id": "<plan task id>",
    "dispatched_at": "<ISO timestamp>",
    "redispatched": false,
    "active_count": 3,
    "completed_count": 0
  },
  "progress": {
    "phase_order": ["brainstorming", "writing-plans", "subagent-driven-development", "completion-gates", "finishing"],
    "completed": [],
    "current": "brainstorming",
    "pending": ["writing-plans", "subagent-driven-development", "completion-gates", "finishing"],
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
    "task-1": { "status": "implementing|spec-reviewing|code-reviewing|done|queued|failed", "agent_id": "<or null>", "attempts": 0 }
  },
  "max_parallel_agents": 5,
  "spec_path": ".claude/specs/<spec-file>",
  "plan_path": ".claude/plans/<plan-file>",
  "decision_trail": ".claude/auto/<task-name>/decisions.md",
  "worktree_path": "<path, if applicable>",
  "stopped_question": null,
  "last_command": null,
  "current_step": "<legal current_step value>",
  "gate_states": {
    "gate_1_tasks_executed": { "passed": false, "iterations": 0 },
    "gate_2_reviews_passed": { "passed": false, "iterations": 0 },
    "gate_3_tests_pass": { "passed": false, "iterations": 0 },
    "gate_4_spec_verified": { "passed": false, "iterations": 0 },
    "gate_5_final_review": { "passed": false, "iterations": 0 },
    "gate_6_git_clean": { "passed": false, "iterations": 0 }
  },
  "reviewer_loop_iterations": {},
  "updated_at": "<ISO timestamp>"
}
```

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
| subagent-driven-development | `dispatch-implementer` |
| subagent-driven-development | `dispatch-parallel` |
| subagent-driven-development | `spec-review-loop` |
| subagent-driven-development | `code-review-loop` |
| completion-gates | `running-gates` |
| finishing | `merging` |

## Status Values and Resume Actions

| `status` | Meaning | Resume Action |
|---|---|---|
| `DECIDING` | In a decision loop (clarifying, approaches, design) | Read `current_step`, `clarifications.md`, and `decisions.md`. Skip decisions already logged. Resume from the step indicated by `current_step`. |
| `AWAITING_SUBAGENT` | (DEPRECATED — use `AWAITING_SUBAGENTS`) Dispatched single subagent, waiting for reply | (1) Run `git log --oneline -3` — if the task's expected commit message appears, the subagent finished before session ended; read code and proceed to review. (2) If no commit found, re-dispatch with same prompt and mark `redispatched: true` in state. |
| `AWAITING_SUBAGENTS` | Multiple subagents dispatched, waiting for any to return | Enumerate `active_agents` array from state.json. For each active agent, check `git log --oneline -3` for that task's expected commit message. Agents whose commits are found → advance their `task_states` entry to the next state (implementing→spec-reviewing; spec-reviewing→code-reviewing; code-reviewing→done), remove from `active_agents`. Agents whose commits are NOT found → re-dispatch with same prompt, keep in `active_agents`, increment `attempts`. After checking all, reconstruct the active pool up to `max_parallel_agents` by dispatching queued tasks from `task_states`. Update `task_states` and `active_agents` in state.json after each batch. |
| `AWAITING_SHELL` | Running a shell command | Read `last_command` from state.json. If idempotent (test, lint, build, search) → re-run. If state-mutating (commit, merge, push, rm, install) → check whether intended state already exists (e.g., `git log --oneline -1` for commit). If already done → skip and proceed. If not done → re-run. |
| `EXECUTING_GATE` | Running completion gate checks | Read `gate_states` from state.json. Resume from the first gate where `passed` is `false`. Do NOT re-check gates where `passed` is `true` — they were verified on disk. |
| `STOPPED_ASK_USER` | Auto-mode stopped to ask user a question | Do NOT auto-resume. Print the stored question (`stopped_question` in state.json) and wait. When user answers, update status to resume from where it stopped. |
| `FINISHING` | In finishing phase (merge) | Re-check git state, continue merge. |
| `DONE` | Pipeline complete | Nothing to do. Print summary. |

## Write Timing for `state.json`

Update `state.json` BEFORE every state transition. Key moments:
- After creating audit directory → write initial state
- Before dispatching subagent (single) → set `AWAITING_SUBAGENT` (legacy)
- Before dispatching parallel subagents → set `AWAITING_SUBAGENTS`, populate `active_agents` with each dispatched agent, update `task_states` for each task
- After each subagent completes → remove from `active_agents`, update `task_states` entry (status, agent_id to null)
- Before running shell command → set `AWAITING_SHELL` + `last_command`
- Before entering a decision → set `DECIDING` + `current_step`
- Between pipeline phases → update `phase`, `progress`
- When stopped to ask user → set `STOPPED_ASK_USER` + `stopped_question`
- After each completion gate → update `gate_states`

## Resume Flow

When resuming (`/auto --resume` or `CCF_AUTO_MODE=1` on startup):

1. Read `.claude/auto/<task-name>/state.json`
2. Read `status`
3. Switch on status (see Status Values table above)
4. Set `phase` to the current pipeline phase from `state.json`. Set `current_step` to the value stored in `state.json` if it is a valid `current_step` for the current phase. If the stored value is invalid or missing, use the first step of that phase (see `current_step` Legal Values table)
5. Update `state.json` BEFORE every subsequent state change

If `.claude/auto/*/state.json` files exist but no specific task was specified for resume: Glob, sort by `updated_at`, pick most recent. Print: "Resuming auto-mode task `<name>` from `<timestamp>`. Use `/auto --new <task>` to start fresh, `/auto --resume <task-name>` to resume a different one, or `/auto --list` to see all."

## What NOT to Do on Resume

- Do NOT blindly "continue working" without reading state
- Do NOT assume subagent results when session ended mid-wait
- Do NOT re-run destructive commands without checking if they already succeeded
- Do NOT skip phases because "we probably already did that"
