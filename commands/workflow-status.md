---
name: workflow-status
description: Show current workflow state — phase, task progress, mode, agent log, metrics, and git context. Read-only diagnostic command.
---

# Workflow Status

Display the current state of the development workflow pipeline.

## Output Sections

### 1. Current Phase
Read `.claude/flow/workflow-state.json` and `.claude/flow/plan-state.json` and display:
- Phase: research / plan / design / impl / review / idle
- Mode: quick / standard / deep / autonomous
- Task progress: x/y tasks completed
- Current agent (if any)
- Retry count
- Verification count and latest verification command/result
- Last updated timestamp
- Plugin workflow active: yes/no based on `.claude/flow/workflow-state.json`
- Structured plan state: status, title, task count, and plan hash if `.claude/flow/plan-state.json` exists
- Planning entry: plugin `/plan`; if host plan mode is active without workflow state, say to exit host plan mode and rerun `/plan <task>`

### 2. Modified Files
Read `.claude/flow/modified-files.jsonl` and display:
- Count of tracked modified files
- List of files (truncated to 20, with "and N more..." if needed)

### 3. Review History
Read `.claude/flow/review-result.txt` if it exists and display:
- Latest review outcome (APPROVE / REQUEST CHANGES / NEEDS DISCUSSION)

### 4. Agent Log
Read `.claude/flow/exec-log.jsonl` (filter `event=agent_complete`) and display:
- Last 10 agent completions with timestamps

### 5. Verification Evidence
Read `.claude/flow/verification-evidence.jsonl` if it exists and display:
- Last 10 test/build/lint/typecheck/git/dev-server commands
- Command kind and pass/fail/unknown status
- Highlight the latest failed verification

### 6. Metrics
Run `python hooks/scripts/metrics.py collect` and display:
- Agent call counts for this session
- Phase durations (if phase transitions recorded)
- Guard block count

### 7. Git Context
Run `git status --short` and `git branch --show-current` to show:
- Current branch
- Uncommitted changes count
- Whether ahead/behind remote

## Usage

```
/workflow-status
```

## Process

1. Check if `.claude/flow/` directory exists
2. If not, report "No plugin workflow state found. Start a workflow with /plan."
3. If yes, read each state file and run metrics collection
4. Format all sections as a clear summary
5. Include whether the user appears to be in plugin workflow state or only host plan mode
6. Do NOT modify any state files — this is a read-only command
