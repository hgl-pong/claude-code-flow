---
name: workflow-plan
description: "Start the full workflow pipeline — skill check, brainstorming, structured plan state, optional architecture/UI design, and approval before implementation."
---

# Workflow Plan

Start the planning pipeline for a feature or task. This is the plugin-side replacement for the built-in plan flow.

## Arguments

```
/workflow-plan [--mode quick|standard|deep|autonomous] <task description>
```

## Process

1. Use `using-claude-code-flow` to select companion skills.
2. **Analyze**: domain (frontend-ui / backend / cross-domain), complexity (1-2 vs 3+ subtasks), and whether the request changes behavior, UI, architecture, or multiple files.
3. **Domain detect**: use Task Domain Detection rules from `dev-orchestrator`. Classify as frontend-UI, backend, or cross-domain.
4. **Brainstorm** if the task is new, behavior-changing, UI-facing, architectural, or a broad refactor. Save substantial designs to `.claude/flow/designs/`.
5. **Select mode**: 1-2 subtasks → quick; 3-5 → standard; 6+ or cross-module → deep; "figure it out" → autonomous.
6. **Set state**: `flow-state.py set-mode <mode>` + `set-phase plan`.
7. **Create structured plan state** with `flow-state.py plan-init`, `plan-update`, and `plan-add-task`.
8. **Evaluate Gate Checklist** (see `dev-orchestrator` Mandatory Gate Checklist). Record checked gates in `phase-context.md`.
9. **Research** (if checked): invoke scout for external info.
10. **Oracle** (if checked): quick→skip unless the user explicitly wants a plan; standard/deep→structured plan → user approval; autonomous→structured plan → auto-approve. Oracle creates tasks via TaskCreate.
11. **Architecture** (if checked): oracle for architecture → approval.
12. **UI Research** (if checked, frontend-UI tasks only): scout research → `ui-research.md`.
13. **UI Design** (if checked, frontend-UI tasks only): designer spec → `DESIGN.md` → approval.
14. **Create execution handoff**: use `writing-plans` for multi-step work, then build self-contained context envelopes for subagents.
15. **Hand off**: frontend-UI→forge after `DESIGN.md`; backend/general→forge; tests/acceptance→prism. Do not skip `writing-plans` for multi-step work that needs coordinated execution.
16. **Quick fix exception**: for a narrow one-file fix with known root cause and no design change, skip the full planning pipeline and go straight to the smallest safe change.
17. **Cross-domain exception**: if the task spans both frontend and backend, split the work by domain and run the applicable gates for each side.
18. **Routing guard**: if the prompt clearly asks for planning, orchestration, or implementation sequencing, prefer `/workflow-plan` over jumping straight into implementation.
19. **Execution rule**: after approval, hand the work to the smallest agent set that matches the file scope; keep parallel work non-overlapping.
20. **Source of truth**: `plan-state.json`, `plan-brief.md`, and `phase-context.md` are the handoff artifacts; do not rely on chat history for execution details.

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer
/workflow-plan --mode quick Fix the memory leak
/workflow-plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
