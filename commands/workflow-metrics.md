---
name: workflow-metrics
description: Show cross-session workflow metrics — completion rates, agent efficiency trends, common failure patterns.
---

# Workflow Metrics

Display aggregated workflow metrics across all sessions.

## Process

1. Run `python hooks/scripts/metrics.py aggregate` to get cross-session metrics
2. If no historical data, report "No historical data yet. Complete a workflow first." and stop
3. Display the following sections:

### Session Overview
- Total sessions
- Completed vs interrupted
- Completion rate percentage

### Agent Efficiency
For each agent that has been used:
- Total calls across all sessions
- Sessions where it was used
- Average calls per session

### Guard Activity
- Total guard hook blocks (commit guard + agent guard)
- If rate is high, suggest reviewing workflow compliance

### Trend Indicators
- Compare recent 5 sessions vs earlier sessions (if enough data)
- Highlight improving/declining metrics

## Usage

```
/workflow-metrics
```

## Notes

- This command is read-only — it never modifies state files
- Metrics are derived from `.claude/flow/exec-log.jsonl`
- Use `/workflow-status` for current session metrics
