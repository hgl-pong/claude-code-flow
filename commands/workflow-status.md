---
name: workflow-status
description: Show current workflow state — phase, task progress, review history, agent log, and git context. Read-only diagnostic command.
---

# Workflow Status

Display the current state of the development workflow pipeline.

## Output Sections

### 1. Current Phase
Read `.claude/flow/workflow-state.json` and display:
- Phase: research / plan / design / impl / review / idle
- Task progress: x/y tasks completed
- Last updated timestamp

### 2. Modified Files
Read `.claude/flow/modified-files.txt` and display:
- Count of tracked modified files
- List of files (truncated to 20, with "and N more..." if needed)

### 3. Review History
Read `.claude/flow/review-result.txt` if it exists and display:
- Latest review outcome (APPROVE / REQUEST CHANGES / NEEDS DISCUSSION)

### 4. Agent Log
Read `.claude/flow/agent-log.txt` if it exists and display:
- Last 10 agent completions with timestamps

### 5. Git Context
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
2. If not, report "No workflow state found. Start a workflow with /workflow-plan."
3. If yes, read each state file and format output
4. Do NOT modify any state files — this is a read-only command
