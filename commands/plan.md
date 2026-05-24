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

- If the request is vague or underspecified, ask blocking clarification questions before writing any plan or code.
- Broad, high-impact, multi-step, cross-domain, unfamiliar, quality-sensitive, or outcome-oriented requests without exact implementation scope are never quick mode.
- For every task that is not very lightweight, do not stop at a chat proposal. Dispatch bounded subagents for research, oracle planning, and applicable design; they must produce the required artifacts in order: clarification notes, local research, material external/domain research, `<output_dir>/plan-brief.md`, applicable domain design artifacts, document self-review `PASS`, then explicit user approval.
- A chat-only design proposal, option list, task list, or main-conversation summary is not a gate artifact and cannot replace subagent-authored `plan-brief.md`, `ui-research.md`, or `DESIGN.md`.
- Frontend/UI/site requests are examples, not the whole rule: include external/UI research and UI `DESIGN.md` when Gate 6 is checked.
- Do not create implementation tasks, ask "confirm and I will start", hand off to implementation, dispatch forge, or edit product files until plan approval and any applicable design approval gates have passed.

## Process

1. Treat `/plan` as the selected route. The entry routing in `dev-orchestrator` has already classified this task, but this command still enforces the hard stops above.
2. Classify only what the planning entry needs: domain (frontend-UI / backend / cross-domain), rough complexity, external-reference presence, and whether the request is truly a quick fix.
3. Select mode using `dev-orchestrator` Mode Selection. For narrow one-file fixes with a known root cause and no design change, redirect to `/quick-fix`.
4. Set state:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
   ```
5. Create or update structured plan state with `flow-state.py plan-init`, `plan-update`, and `plan-add-task`.
6. Evaluate gates from `skills/dev-orchestrator/references/pipeline-operations.md`. That file is the source of truth for research, workflow-intake, oracle, UI design, document review, review, and acceptance ordering; do not duplicate the full checklist here.
7. For every task that is not very lightweight, create planning-stage TaskCreate records and dispatch subagents: general-purpose research first, then oracle for `plan-brief.md`, then applicable design/ui-design work. Do not collapse these into main-conversation prose.
8. Record checked gates, subagent owners, artifact paths, and self-review status in `<output_dir>/phase-context.md` (normally `.claude/flow/plans/<slug>/`).
9. Let `oracle` produce `<output_dir>/plan-brief.md` for standard/deep/autonomous planning. Use `planning` skill when approved requirements need executable task breakdown.
9. After approval, hand execution to `dev-orchestrator`; it owns DAG-aware scheduling, agent envelopes, review, and acceptance.
10. Built-in plan guard: do not invoke `EnterPlanMode`. If Claude Code host plan mode is already active, tell the user to exit host plan mode and rerun `/plan <task>`.

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
