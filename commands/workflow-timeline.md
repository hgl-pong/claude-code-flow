---
name: workflow-timeline
description: Show the full execution timeline for the current or most recent workflow session.
---

# Workflow Timeline

Display a chronological timeline of all workflow events for the current session.

## Process

1. Run `python hooks/scripts/metrics.py raw 50` to get recent execution log entries
2. If no entries, report "No timeline data available."
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
4. Color-code by event type:
   - session_start/end: neutral
   - phase_transition: blue
   - agent_complete: green (success)
   - tool_guard_block: red
   - review_result: yellow
   - error: red
5. If available, show duration between phase transitions
6. Show total session duration at the end

## Usage

```
/workflow-timeline
```

## Notes

- Read-only command — never modifies state
- Data sourced from `.claude/flow/exec-log.jsonl`
- Use `/workflow-status` for current state snapshot
- Use `/workflow-metrics` for cross-session analysis
