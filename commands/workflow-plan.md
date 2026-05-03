---
name: workflow-plan
description: "Start the full workflow pipeline — skill check, brainstorming, oracle planning, optional architecture/UI design, and approval before implementation."
---

# Workflow Plan

Start the planning pipeline for a feature or task.

## Arguments

```
/workflow-plan [--mode quick|standard|deep|autonomous] <task description>
```

## Process

1. Use `using-claude-code-flow` to select companion skills.
2. **Analyze**: domain (frontend-ui / backend / cross-domain), complexity (1-2 vs 3+ subtasks), needs design/research?
3. **Domain detect**: use Task Domain Detection rules from `dev-orchestrator`. Classify as frontend-UI, backend, or cross-domain.
4. **Brainstorm** if needed: new features, behavior changes, UI work, architecture, broad refactors. Save substantial designs to `docs/superpowers/specs/`.
5. **Select mode**: 1-2 subtasks → quick; 3-5 → standard; 6+ or cross-module → deep; "figure it out" → autonomous.
6. **Set state**: `flow-state.py set-mode <mode>` + `set-phase plan`
7. **Evaluate Gate Checklist** (see `dev-orchestrator` Mandatory Gate Checklist). Record checked gates in `phase-context.md`.
8. **Research** (if checked): invoke scout for external info.
9. **Oracle** (if checked): quick→skip unless user explicitly requests a plan; standard/deep→markdown plan→user approval; autonomous→markdown plan→auto-approve. Use HTML visualization only when the user explicitly requests it. Oracle creates tasks via TaskCreate.
10. **Architecture** (if checked): atlas for architecture → approval.
11. **UI Research** (if checked, frontend-UI tasks only): scout research → `ui-research.md`.
12. **UI Design** (if checked, frontend-UI tasks only): designer spec → `DESIGN.md` → approval.
13. **Create execution handoff**: use `writing-plans` for multi-step work, then build self-contained context envelopes for subagents.
14. **Hand off**: frontend-UI→weaver after `DESIGN.md`; backend/general→forge; tests→prism; build/config→anvil.

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer
/workflow-plan --mode quick Fix the memory leak
/workflow-plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
