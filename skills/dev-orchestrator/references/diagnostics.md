# Workflow Diagnostics Reference

Shared source of truth for read-only workflow diagnostic commands.

## Scope

Diagnostics answer three questions:

| Command | Question | Primary source |
|---|---|---|
| `/workflow-status` | What is happening now? | `.claude/flow/workflow-state.json`, `.claude/flow/plan-state.json`, `metrics.py collect` |
| `/workflow-timeline` | What happened recently? | `python hooks/scripts/metrics.py raw 50` |
| `/workflow-metrics` | What patterns appear across sessions? | `python hooks/scripts/metrics.py aggregate` |

All diagnostic commands are read-only. They must not create, mutate, archive, or delete workflow state.

## Runtime Files

| File | Use |
|---|---|
| `.claude/flow/workflow-state.json` | Current phase, mode, task progress, current agent, retries, verification summary |
| `.claude/flow/plan-state.json` | Structured plan status, title, task count, and plan hash |
| `.claude/flow/modified-files.jsonl` | Workflow-tracked modified files |
| `.claude/flow/review-result.txt` | Latest review outcome |
| `.claude/flow/verification-evidence.jsonl` | Test/build/lint/typecheck/git/dev-server evidence |
| `.claude/flow/exec-log.jsonl` | Append-only event log for agents, phases, guards, reviews, verification, session lifecycle |

Missing files are normal. Report absence clearly instead of treating it as an error.

## Metrics Script Contract

Use `hooks/scripts/metrics.py` for derived diagnostics:

| Command | Output |
|---|---|
| `python hooks/scripts/metrics.py collect` | Latest session metrics: agent counts, phase durations, guard blocks, review count, verification counts |
| `python hooks/scripts/metrics.py aggregate` | Cross-session totals: completion rate, global agent stats, guard totals, verification totals |
| `python hooks/scripts/metrics.py raw 50` | Last 50 execution log entries for timeline display |

Do not reimplement these aggregations inside command docs. If the metric contract changes, update `metrics.py` and this reference first.

## Output Rules

- Always state whether plugin workflow state is active.
- Prefer exact counts and timestamps over narrative guesses.
- Show latest failures prominently for verification evidence.
- Include git branch and dirty count when showing current status.
- For host plan mode without plugin workflow state, tell the user to exit host plan mode and rerun `/plan <task>`.
- Keep output concise: current status first, then supporting history or metrics.

## Command Boundaries

- `/workflow-status` may summarize latest timeline and metrics, but it should optimize for the current snapshot.
- `/workflow-timeline` may mention current phase if visible in events, but it should optimize for chronological execution history.
- `/workflow-metrics` may mention current session totals, but it should optimize for cross-session trends.
- Use `/workflow-resume` for state restoration. Diagnostic commands must not resume or alter workflows.
