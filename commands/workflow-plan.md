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
8. **Evaluate Gate Checklist** (see `dev-orchestrator` Mandatory Gate Checklist). Record checked gates in `<output_dir>/phase-context.md` (e.g. `.claude/flow/plans/<slug>/`).
9. **Research** (if checked): invoke scout for **both** local codebase analysis and external web research. Scout MUST complete before oracle starts — these are sequential, never parallel. Scout findings feed directly into oracle's planning context.
10. **Oracle** (if checked): quick→skip unless the user explicitly wants a plan; standard/deep→structured plan; autonomous→structured plan. Oracle creates tasks via TaskCreate. Oracle runs **after** scout completes, using scout's findings as input.
11. **Architecture** (if checked): oracle for architecture.
12. **UI Research** (if checked, frontend-UI tasks only): scout produces `ui-research.md` covering: (a) local codebase patterns, (b) 2-3 competitor product UI analysis, (c) current design aesthetics and trends relevant to the product domain. Must complete before UI Design gate.
13. **UI Design** (if checked, frontend-UI tasks only): `ui-design` skill → `DESIGN.md`.
14. **Document auto-review**: if any gate produced documents (plan-brief.md, phase-context.md, DESIGN.md), invoke sentinel with `review_focus: document_quality`. Pass original task description in the envelope. If REQUEST CHANGES → oracle revises → re-review (max 3 rounds). Still failing after 3 rounds → escalate to user. Only proceed to approval gate after APPROVE.
15. **Create execution handoff**: use `writing-plans` for multi-step work, then build self-contained context envelopes for subagents.
16. **Hand off**: frontend-UI→forge after `DESIGN.md`; backend/general→forge; tests/acceptance→prism. Do not skip `writing-plans` for multi-step work that needs coordinated execution.
17. **Quick fix exception**: for a narrow one-file fix with known root cause and no design change, skip the full planning pipeline and go straight to the smallest safe change.
18. **Cross-domain exception**: if the task spans both frontend and backend, split the work by domain and run the applicable gates for each side.
19. **Routing guard**: if the prompt clearly asks for planning, orchestration, or implementation sequencing, prefer `/workflow-plan` over jumping straight into implementation.
20. **Execution rule**: after approval, hand the work to the smallest agent set that matches the file scope; keep parallel work non-overlapping.
21. **Source of truth**: `plan-state.json`, `<output_dir>/plan-brief.md`, and `<output_dir>/phase-context.md` are the handoff artifacts; do not rely on chat history for execution details.

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer
/workflow-plan --mode quick Fix the memory leak
/workflow-plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
