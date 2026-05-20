---
name: workflow-timeline
description: Show the full execution timeline for the current or most recent workflow session.
---

# Workflow Timeline

Display a chronological timeline of all workflow events for the current session.

Use `skills/dev-orchestrator/references/diagnostics.md` as the source of truth for timeline inputs, runtime files, and command boundaries.

## Process

1. Run `python hooks/scripts/metrics.py raw 50` to get recent execution log entries.
2. If no entries exist, report "No timeline data available."
3. Display events in chronological order, formatted as a timeline:
   ```
   10:00:00 [session_start] branch=main
   10:00:05 [phase_transition] idle -> plan
   10:00:10 [agent_complete] oracle (opus) - success
   10:05:30 [phase_transition] plan -> impl
   10:05:35 [agent_complete] forge (sonnet) - success
   ...
   10:30:00 [workflow_stop] phase=review tasks=5/5 modified=8
   ```
4. Highlight important event types: session lifecycle, phase transitions, agent completion, guard blocks, review results, verification evidence, and errors.
5. If available, show duration between phase transitions.
6. Show total session duration at the end.
7. Do not modify any state files; this is a read-only command.

## Usage

```
/workflow-timeline
```

## Notes

- Data is sourced from `.claude/flow/exec-log.jsonl`.
- Use `/workflow-status` for current state snapshot.
- Use `/workflow-metrics` for cross-session analysis.
