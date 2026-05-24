---
name: plan
description: "Start the plugin planning pipeline: routed planning, optional brainstorming, structured plan state, optional architecture/UI design, and approval before implementation."
argument-hint: "[--mode quick|standard|deep|autonomous] <task>"
allowed-tools:
  - Agent
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - TaskCreate
  - TaskUpdate
  - Bash(rtk python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py*)
---

# Plan

Start the plugin planning pipeline for a feature or task. This is the plugin-side replacement for Claude Code's built-in plan flow.

## Arguments

```
/plan [--mode quick|standard|deep|autonomous] <task description>
```

## Hard Stops

Use `skills/dev-orchestrator/references/pipeline-operations.md` as the source of truth for clarification, lightweight/non-trivial classification, research, oracle planning, design approval, document self-review, and implementation blocking. This command must not duplicate the full gate checklist.

Do not invoke `EnterPlanMode`. Do not edit implementation files until the required plan and design gates pass.

## Process

1. Treat `/plan` as the selected route.
2. Set state:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
   ```
3. Create or update structured plan state with `flow-state.py plan-init`, `plan-update`, and `plan-add-task`.
4. Evaluate gates from `skills/dev-orchestrator/references/pipeline-operations.md`.
5. Record checked gates, owners, artifact paths, and self-review status in `<output_dir>/phase-context.md` (normally `.claude/flow/plans/<slug>/`).
6. Let `oracle` produce `<output_dir>/plan-brief.md` when Gate 3 is checked. Use `planning` skill when approved requirements need executable task breakdown.
7. After approval, hand execution to `dev-orchestrator`; it owns DAG-aware scheduling, agent envelopes, review, and acceptance.
8. Built-in plan guard: do not invoke `EnterPlanMode`. If Claude Code host plan mode is already active, tell the user to exit host plan mode and rerun `/plan <task>`.

## Source of Truth

- Gate checklist and ordering: `skills/dev-orchestrator/references/pipeline-operations.md`
- Execution orchestration: `skills/dev-orchestrator/SKILL.md`
- Subagent prompt templates: `skills/dev-orchestrator/references/subagent-prompts.md`
- Plan state and brief export: `.claude/flow/plan-state.json`, `.claude/flow/workflow-state.json`, and `<output_dir>/plan-brief.md`

## Usage

```
/plan Add user authentication with OAuth and JWT
/plan --mode deep Refactor the database layer
/plan --mode quick Fix the memory leak
/plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
