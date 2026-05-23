---
name: workflow-status
description: Show current workflow state: phase, task progress, mode, agent log, metrics, and git context. Read-only diagnostic command.
allowed-tools:
  - Read
  - Bash(rtk python hooks/scripts/metrics.py collect*)
  - Bash(rtk git status*)
---

# Workflow Status

Display the current state of the development workflow pipeline.

Use `skills/dev-orchestrator/references/diagnostics.md` as the source of truth for runtime files, metrics commands, and output rules.

## Output Focus

Show the current snapshot first:

- workflow active/inactive state
- `Plugin workflow active`: yes/no
- current phase, mode, task progress, current agent, retries
- structured plan state when present
- latest review and verification status
- tracked modified files
- current-session metrics from `python hooks/scripts/metrics.py collect`
- git branch and dirty count

## Usage

```
/workflow-status
```

## Process

1. Check if `.claude/flow/` directory exists.
2. If not, report "No plugin workflow state found. Start a workflow with /plan."
3. If yes, follow the diagnostics reference and run metrics collection.
4. Format all sections as a clear summary.
5. Include whether the user appears to be in plugin workflow state or only host plan mode.
6. Do not modify any state files; this is a read-only command.
