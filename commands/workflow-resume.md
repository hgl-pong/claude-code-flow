---
name: workflow-resume
description: Resume an interrupted workflow from the latest snapshot. Restores phase, task progress, and context.
allowed-tools:
  - Read
  - Glob
  - Bash(rtk git status*)
  - Bash(rtk python hooks/scripts/flow-state.py*)
---

# Workflow Resume

Resume an interrupted workflow from the most recent state snapshot.

## Process

1. Run `rtk python hooks/scripts/flow-state.py list-snapshots` to check available snapshots
2. If no snapshots exist, report "No interrupted workflows found." and stop
3. If snapshots exist, display the most recent snapshot's details:
   - Phase the workflow was in
   - Task progress (x/y completed)
   - Mode (quick/standard/deep/autonomous)
   - Last updated timestamp
   - `resume_cursor.current_gate`
   - `resume_cursor.next_action`
   - ready/blocked task IDs
   - active batch and agent dispatch IDs if present
4. Ask the user to confirm: "Resume this workflow? (The state will be restored)"
5. If confirmed, run `rtk python hooks/scripts/flow-state.py resume`
6. Read `.claude/flow/workflow-state.json` first; treat `resume_cursor.next_action` as the recommended next machine step
7. Read `.claude/flow/plan-state.json`; use `output_dir` when present, otherwise check the latest `.claude/flow/plans/*` directory
8. Read the matching `phase-context.md` and `plan-brief.md` when present; for autonomous work, also check `.claude/flow/uli/<task-slug>/phase-context.md` if the state names a task slug
9. Display a restored summary:
   - current gate/phase
   - next action
   - ready tasks to dispatch
   - blocked tasks and blockers
   - latest checkpoint path
   - verification evidence status
10. Continue from `next_action`; do not rerun completed side-effect steps unless the event log shows no successful entry.

## Usage

```
/workflow-resume
```
