---
name: workflow-metrics
description: Show cross-session workflow metrics: completion rates, agent efficiency trends, common failure patterns.
---

# Workflow Metrics

Display aggregated workflow metrics across all sessions.

Use `skills/dev-orchestrator/references/diagnostics.md` as the source of truth for metrics script contracts, runtime files, and command boundaries.

## Process

1. Run `python hooks/scripts/metrics.py aggregate` to get cross-session metrics.
2. If no historical data exists, report "No historical data yet. Complete a workflow first." and stop.
3. Display cross-session session overview, agent efficiency, guard activity, verification totals, and trend indicators when enough data exists.
4. Do not modify any state files; this is a read-only command.

## Usage

```
/workflow-metrics
```

## Notes

- Metrics are derived from `.claude/flow/exec-log.jsonl`.
- Use `/workflow-status` for current session metrics.
- Use `/workflow-timeline` for chronological event history.
