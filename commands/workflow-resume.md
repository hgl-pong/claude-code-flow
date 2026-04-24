---
name: workflow-resume
description: Resume an interrupted workflow from the latest snapshot. Restores phase, task progress, and context.
---

# Workflow Resume

Resume an interrupted workflow from the most recent state snapshot.

## Process

1. Run `python hooks/scripts/flow-state.py list-snapshots` to check available snapshots
2. If no snapshots exist, report "No interrupted workflows found." and stop
3. If snapshots exist, display the most recent snapshot's details:
   - Phase the workflow was in
   - Task progress (x/y completed)
   - Mode (quick/standard/deep/autonomous)
   - Last updated timestamp
4. Ask the user to confirm: "Resume this workflow? (The state will be restored)"
5. If confirmed, run `python hooks/scripts/flow-state.py resume`
6. Read `.claude/flow/phase-context.md` if it exists to recover the plan/architecture context
7. Display a summary of what was restored and suggest next steps based on the phase:
   - `plan` → "Plan was in progress. Re-run /workflow-plan to continue."
   - `design` → "Architecture design was in progress. Re-run the design step."
   - `impl` → "Implementation was in progress. Review modified files and continue with forge."
   - `review` → "Review was in progress. Check review-result.txt and continue."
   - `idle` → "Workflow was completed. No action needed."

## Usage

```
/workflow-resume
```
