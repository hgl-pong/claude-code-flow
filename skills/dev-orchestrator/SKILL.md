---
name: Dev Orchestrator
version: "4.1.0"
description: "Use when executing multi-step development tasks through the agent pipeline"
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and error recovery.

## Mode Selection

Auto-recommend: 1-2 subtasks → **quick**; 3-5 → **standard**; 6+ or cross-module → **deep**; "just ship it" → **autonomous**; `ulw`/`ultrawork` → **ultrawork**; `uli` → **uli**.

| Mode | Research | Architecture | UI Design | Plan Approval | Review | Auto-retry |
|------|----------|-------------|-----------|---------------|--------|------------|
| quick | No | No | No | No | Optional | No |
| standard | If needed | If needed | Yes for UI | Yes | Yes | No |
| deep | Yes | Yes | Yes for UI | Yes (MD) | Yes | Yes |
| autonomous | Auto | Auto | Auto for UI | Auto | Auto (max 3) | Yes |

"If needed": evaluate the condition. If true, the gate is MANDATORY.

## Agent Roster

| Agent | Model | Effort | Role | Gate |
|-------|-------|--------|------|------|
| `scout` | haiku | default | Research, analysis | Research |
| `oracle` | opus | xhigh | Planning + architecture | Plan/Design |
| `forge` | sonnet | high | Full-stack implementation | Impl |
| `prism` | sonnet | high | Tests, build, acceptance | Tests/Acceptance |
| `sentinel` | sonnet | high | Code review (two-stage) | Review |

## Pipeline Steps

### 1. Analyze + Mode + Domain
Start with `using-claude-code-flow`. Classify domain (frontend-UI / backend / cross-domain), complexity, select mode. For new features: run `brainstorming` first.

### 2. Evaluate Gates → 3-8. Execute Gates
See `references/pipeline-operations.md` for full gate checklist and execution details. Record in `<output_dir>/phase-context.md`.

Key rules:
- **Plan Gate**: oracle creates plan-brief.md + TaskCreate with blockedBy
- **UI Design Gate**: forge MAY NOT dispatch until DESIGN.md exists
- **Review Gate**: two-stage (spec compliance → code quality). NEVER reverse order.

### 9. Implementation Loop
```
FOR each task batch:
  1. PICK — TaskList → pending, unblocked
  2. ANALYZE — extract file paths, build conflict graph
  3. ENVELOPE — construct self-contained prompt
  4. DISPATCH — fire non-conflicting agents in one message
  5. WAIT — system notifies on completion
  6. VERIFY — check output + FILES_MODIFIED
  7. RECORD — TaskUpdate + evidence
  8. LOOP — fresh context, no prior agent output
```

For 3+ subtasks: invoke `dispatching-parallel-agents` for batch grouping and conflict isolation.

### 10-11. Review + Acceptance
Two-stage sentinel review, then prism acceptance. See `references/pipeline-operations.md`.

### 12. Report
Concise: outcome, files changed, verification, caveats.

## Verification

**NEVER claim completion without fresh verification evidence.** TaskUpdate completed only after prism ACCEPT.

## Red Flags — STOP

- "I'll skip review for this small change"
- "The agent output looks fine, I don't need to verify FILES_MODIFIED"
- "I'll carry this context into the next agent dispatch"
- "Stage 1 and Stage 2 can run together"
- "This frontend task doesn't need ui-design skill" ← if UI Design gate checked → run it
- "I'll dispatch forge for UI work without DESIGN.md" ← WRONG

## References

- `references/pipeline-operations.md` — Gate checklist, execution details, context envelope template
- `references/subagent-prompts.md` — Prompt templates for forge, sentinel, prism, scout dispatch

Plan authority lives in `plan-state.json` and `workflow-state.json`. The agent-readable brief exports to `<output_dir>/plan-brief.md`.
