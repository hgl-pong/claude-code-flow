---
name: workflow-plan
description: "Start the full workflow pipeline: routed planning, optional brainstorming, structured plan state, optional architecture/UI design, and approval before implementation."
---

# Workflow Plan

Start the planning pipeline for a feature or task. This is the plugin-side replacement for the built-in plan flow.

## Arguments

```
/workflow-plan [--mode quick|standard|deep|autonomous] <task description>
```

## Process

1. Treat `/workflow-plan` as the selected route. If no command or hook already routed the prompt, do one `using-claude-code-flow` pass; otherwise do not invoke it again.
2. **Analyze**: domain (frontend-ui / backend / cross-domain), complexity (1-2 vs 3+ subtasks), and whether the request changes behavior, UI, architecture, or multiple files.
3. **Domain detect**: use Task Domain Detection rules from `dev-orchestrator`. Classify as frontend-UI, backend, or cross-domain.
4. **External reference check**: if the task says to reference, borrow from, port, import, compare with, or optimize from another repo/plugin/workflow, mark Gate 2a (Reference Intake) as checked. Intake runs after Research when both gates are checked, otherwise immediately before Oracle.
5. **Brainstorm only when needed**: use `brainstorming` if the task has unresolved product/design decisions, is exploratory, or needs a spec before planning. Skip it for approved requirements, direct execution, narrow fixes, routine maintenance, or a saved spec. Save design specs to `.claude/flow/designs/<topic>-design.md`. Note: design specs are not `DESIGN.md` (the design system token document).
6. **Select mode**: 1-2 subtasks -> quick; 3-5 -> standard; 6+ or cross-module -> deep; "figure it out" -> autonomous.
7. **Set state**: `flow-state.py set-mode <mode>` + `set-phase plan`.
8. **Create structured plan state** with `flow-state.py plan-init`, `plan-update`, and `plan-add-task`.
9. **Evaluate Gate Checklist** (see `dev-orchestrator` Mandatory Gate Checklist). Record checked gates in `<output_dir>/phase-context.md` (e.g. `.claude/flow/plans/<slug>/`).
10. **Research** (if checked): invoke research subagent (`subagent_type: "general-purpose"` with research skill methodology inlined) for **both** local codebase analysis and external web research. **NEVER use `subagent_type: "claude-code-flow:research"`; that agent type does not exist.** Research MUST complete before oracle starts; these are sequential, never parallel. Research findings feed directly into oracle's planning context.
11. **Reference Intake** (if checked): use `workflow-intake`; write `<output_dir>/intake-decision.md`; classify each idea as Adopt / Adapt / Reject / Defer. Do not import wholesale agent catalogs, command catalogs, hook systems, or external runtimes.
12. **Oracle** (if checked): quick -> skip unless the user explicitly wants a plan; standard/deep -> structured plan; autonomous -> structured plan. Oracle creates tasks via TaskCreate. Oracle runs **after** research and intake complete, using both as input when present.
13. **Architecture** (if checked): oracle for architecture.
14. **UI Research** (if checked, frontend-UI tasks only): research subagent produces `ui-research.md` covering: (a) local codebase patterns, (b) 2-3 competitor product UI analysis, (c) current design aesthetics and trends relevant to the product domain. Must complete before UI Design gate.
15. **UI Design** (if checked, frontend-UI tasks only): `ui-design` skill -> `DESIGN.md` at **project root** (alongside CLAUDE.md, NOT inside `.claude/`).
16. **Document auto-review**: if any gate produced documents (intake-decision.md, plan-brief.md, phase-context.md, DESIGN.md), invoke sentinel with `review_focus: document_quality`. Pass original task description in the envelope. If REQUEST CHANGES -> oracle revises -> re-review (max 3 rounds). Still failing after 3 rounds -> escalate to user. Only proceed to approval gate after APPROVE.
17. **Create execution handoff**: use `writing-plans` for multi-step work, then hand execution to `dev-orchestrator` with self-contained context envelopes for subagents.
18. **Hand off**: `dev-orchestrator` owns coordinated execution. It dispatches frontend-UI -> forge after `DESIGN.md`, backend/general -> forge, and tests/acceptance -> prism. Do not skip `writing-plans` for multi-step work that needs coordinated execution.
19. **Quick fix exception**: for a narrow one-file fix with known root cause and no design change, skip the full planning pipeline and go straight to the smallest safe change.
20. **Cross-domain exception**: if the task spans both frontend and backend, split the work by domain and run the applicable gates for each side.
21. **Routing guard**: if the prompt clearly asks for planning, orchestration, or implementation sequencing, prefer `/workflow-plan` over jumping straight into implementation.
22. **Execution rule**: after approval, hand the work to the smallest agent set that matches the file scope; keep parallel work non-overlapping.
23. **Source of truth**: `plan-state.json`, `<output_dir>/plan-brief.md`, `<output_dir>/phase-context.md`, and `<output_dir>/intake-decision.md` when present are the handoff artifacts; do not rely on chat history for execution details.

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer
/workflow-plan --mode quick Fix the memory leak
/workflow-plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
