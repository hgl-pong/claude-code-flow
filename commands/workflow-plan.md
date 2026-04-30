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
2. **Analyze**: domain (frontend-ui / backend), complexity (1-2 vs 3+ subtasks), needs design/research?
3. **Brainstorm** if needed: new features, behavior changes, UI work, architecture, broad refactors. Save substantial designs to `docs/superpowers/specs/`.
4. **Select mode**: 1-2 subtasks → quick; 3-5 → standard; 6+ or cross-module → deep; "figure it out" → autonomous.
5. **Set state**: `flow-state.py set-mode <mode>` + `set-phase plan`
6. **Research** (if needed, not quick): invoke scout for external info.
7. **Oracle**: quick→inline plan; standard→text summary→user approval; deep→HTML viz→review; autonomous→auto-approve. Oracle creates tasks via TaskCreate.
8. **Design** (deep/autonomous + new system): atlas for architecture → approval.
9. **UI Design** (frontend-ui, standard+): scout research → designer spec → approval.
10. **Create execution plan**: `writing-plans` for multi-step work.
11. **Hand off**: frontend-UI→weaver; backend→forge; tests→prism; build→anvil.

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer
/workflow-plan --mode quick Fix the memory leak
/workflow-plan --mode autonomous Build a REST API
```

After plan approval, see `dev-orchestrator` for DAG-aware implementation scheduling.
