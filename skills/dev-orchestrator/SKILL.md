---
name: Dev Orchestrator
version: "4.0.0"
description: "Use for: multi-step development tasks, agent orchestration, pipeline management, DAG scheduling, parallel execution."
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and error recovery.

## Capability Tiers

**Standalone** (always works):
- Mode selection, domain detection, gate checklist, sequential pipeline execution
- Agent dispatch with context envelopes, task management via TaskCreate/TaskUpdate

**Enhanced** (with connected tools):
- + GitNexus: impact analysis before agent dispatch, execution flow tracing for debugging
- + Tavily: external research via scout for technology comparisons
- + Design Server: interactive design token viewer for UI tasks

## Communication Style

Keep user-facing updates concise. Report outcomes, changed files, verification, and blockers. Avoid explaining the pipeline unless asked. Routine success: 3-6 bullets or 1-2 short paragraphs.

## Mode Selection

Auto-recommend: 1-2 subtasks → **quick**; 3-5 → **standard**; 6+ or cross-module → **deep**; "just ship it" → **autonomous**; `ulw`/`ultrawork` → **ultrawork**; `uli` → **uli**.

| Mode | Research | Architecture | UI Research | UI Design | Plan Approval | Review | Auto-retry |
|------|----------|-------------|-------------|-----------|---------------|--------|------------|
| quick | No | No | No | No | No | Optional | No |
| standard | If needed | If needed | Yes for UI | Yes for UI | Yes | Yes | No |
| deep | Yes | Yes | Yes for UI | Yes for UI | Yes (MD) | Yes | Yes |
| autonomous | Auto | Auto | Auto for UI | Auto for UI | Auto | Auto (max 3) | Yes |

"If needed": evaluate the condition. If true, the gate is MANDATORY.

Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <mode>`

## Agent Roster

| Agent | Model | Effort | Role | Gate |
|-------|-------|--------|------|------|
| `scout` | haiku | default | Research, analysis, product state | Research |
| `oracle` | opus | xhigh | Planning + architecture + UI design decision | Plan/Design |
| `forge` | sonnet | high | Full-stack implementation | Impl |
| `prism` | sonnet | high | Tests, build, acceptance | Tests/Build/Acceptance |
| `sentinel` | sonnet | high | Code review (two-stage) | Review |

**Skills (non-agent):** `ui-design` skill — oracle decides whether to invoke during planning for frontend-UI tasks.

## Task Domain Detection

**Frontend-UI**: creates/modifies UI files (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`), involves components/layouts/styling, mentions "design"/"UI"/"frontend"/"component".

**Backend**: creates/modifies API endpoints, database queries, server logic, scripts, `.py`/`.go`/`.rs`/`.ts` outside UI layer.

**Cross-domain**: both. Split into frontend/backend subtasks, run applicable gates for each.

## Pipeline Steps

### 1. Analyze + Mode + Domain
Start with `using-claude-code-flow`. Classify domain, complexity, select mode. For new features/behavior changes/UI work: run `brainstorming` first.

### 2. Evaluate Gate Checklist
See `${CLAUDE_PLUGIN_ROOT}/skills/dev-orchestrator/references/pipeline-operations.md` for full gate checklist. Record checked gates in `<output_dir>/phase-context.md` (e.g. `.claude/flow/plans/<slug>/`). Plan authority lives in `plan-state.json` and `workflow-state.json`.

### 3-8. Execute Gates in Order
Run checked gates sequentially. Each gate agent appends output to `<output_dir>/phase-context.md`.

Key rules:
- **Plan Gate**: oracle creates `<output_dir>/plan-brief.md` + TaskCreate tasks with blockedBy
- **UI Design Gate**: if oracle determined UI design is needed, `ui-design` skill produces DESIGN.md before forge dispatches. IRON LAW for UI tasks: forge MAY NOT dispatch until DESIGN.md exists.
- **Review Gate**: two-stage (spec compliance → code quality). NEVER reverse order. See `pipeline-operations.md` for subagent-driven review in deep/autonomous mode.

### 9. Implementation (Ralph Loop)
Set phase to `impl`. Apply `testing-strategy` before production code. For bugs with unknown cause, apply `systematic-debugging` first.

For large tasks (3+ subtasks): invoke `dispatching-parallel-agents` skill before the first dispatch — it determines batch groupings, file conflict isolation, and inter-agent handoff contracts.

**Stateless iteration:**
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

Context envelope template and dispatch details: `${CLAUDE_PLUGIN_ROOT}/skills/dev-orchestrator/references/pipeline-operations.md`.

### 10. Review Gate (if checked)
Two-stage sentinel review. See `pipeline-operations.md` for subagent-driven mode.

### 11. Acceptance Gate (if checked)
Prism reads `<output_dir>/plan-brief.md`, runs build+tests, checks feature delivery. ACCEPT→complete; REJECT→back to implementer (max 2 rounds).

### 12. Report
Concise summary: outcome, files changed, verification results, caveats.

## Verification

**IRON LAW: NEVER claim completion without fresh verification evidence.**

- "Tests pass" → actual test output
- "Build succeeds" → actual build output
- "Implementation matches plan" → line-by-line comparison
- TaskUpdate completed only after prism ACCEPT

### Red Flags — STOP and re-read if you catch yourself:

- "I'll skip review for this small change"
- "The agent output looks fine, I don't need to verify FILES_MODIFIED"
- "I'll carry this context into the next agent dispatch"
- "Stage 1 and Stage 2 can run together"
- "This frontend task doesn't need ui-design skill" ← UI Design gate checked → run it
- "I'll dispatch forge for UI work without DESIGN.md" ← WRONG
