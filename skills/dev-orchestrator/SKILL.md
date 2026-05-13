---
name: Dev Orchestrator
version: "4.2.0"
description: "Use by default for executing implementation work, approved plans, multi-step tasks, feature delivery, cross-file changes, end-to-end fixes, agent orchestration, or any task that needs planning-to-implementation-to-test-to-review coordination."
argument-hint: "<task description, approved plan, feature, fix, refactor, or delivery goal>"
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, selective external-intake, DAG-aware scheduling, and error recovery.

## Trigger Bias

Default to this skill whenever the user is asking to **do the work**, not merely discuss it. If a request includes implementation, execution, feature delivery, fixing, refactoring, testing handoff, review handoff, multi-file edits, multiple subtasks, or "finish/ship/deliver this", `dev-orchestrator` should be considered active even when `/workflow-plan` or another process skill also applies.

Strong trigger phrases include:

- "execute the plan", "implement this", "build this", "ship it", "deliver end-to-end"
- "multi-step", "multiple files", "full-stack", "cross-domain", "coordinate agents"
- "run the pipeline", "orchestrate", "plan then implement", "fix and verify"
- "after approval", "use forge/prism/sentinel", "handoff to agents"

Use `workflow-plan` first only when the user is asking primarily for a plan, proposal, or approval gate. Once execution is requested or an approved plan exists, hand to `dev-orchestrator`.

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
| `oracle` | opus | xhigh | Planning + architecture | Plan/Design |
| `forge` | sonnet | high | Full-stack implementation | Impl |
| `prism` | sonnet | high | Tests, build, acceptance | Tests/Acceptance |
| `sentinel` | sonnet | high | Code review (two-stage) | Review |

Research is dispatched as **general-purpose subagents** using the `research` skill methodology. No dedicated agent needed — see `skills/research/references/dispatch-templates.md`. **NEVER use `subagent_type: "claude-code-flow:research"` — always use `subagent_type: "general-purpose"` with research methodology inlined in the prompt.**

External workflow references are handled by the `workflow-intake` skill before oracle planning. They are source material, not authority. Intake must strengthen the existing `oracle -> forge -> prism -> sentinel` pipeline and must not create a competing ECC-style surface.

## Pipeline Steps

### 1. Analyze + Mode + Domain
If `dev-orchestrator` was selected by a command, hook, or prior `using-claude-code-flow` pass, continue directly here; do not invoke `using-claude-code-flow` again. Classify domain (frontend-UI / backend / cross-domain), complexity, and mode. For new ambiguous features or substantial design decisions, run `brainstorming` first; skip it for approved specs/plans, narrow fixes, direct execution, and routine maintenance. If the request references another repo, agent pack, plugin, or workflow, run `workflow-intake` before oracle planning and pass its adopt/adapt/reject decisions into the plan context.

### 2. Evaluate Gates → 3-8. Execute Gates
See `references/pipeline-operations.md` for full gate checklist and execution details. Record in `<output_dir>/phase-context.md`.

Key rules:
- **Reference Intake Gate → Plan Gate**: outside repos or workflow packs are inspected selectively. Record accepted, adapted, rejected, and deferred ideas in `intake-decision.md`. Do not copy wholesale agent catalogs, command catalogs, hook systems, or runtime dependencies into this workflow.
- **Research Gate → Plan Gate**: research subagent and oracle are STRICTLY SEQUENTIAL. Research must finish both local codebase analysis and external web research before oracle starts. Never dispatch them in parallel. Oracle receives research findings as direct input.
- **Plan Gate**: oracle creates plan-brief.md + TaskCreate with blockedBy
- **UI Design Gate**: forge MAY NOT dispatch until `DESIGN.md` exists at project root (not inside `.claude/`)
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
- "This external workflow is popular, so I'll import its agents/commands wholesale"
- "A new external runtime is fine because the reference repo uses it"
- "Stage 1 and Stage 2 can run together"
- "This frontend task doesn't need ui-design skill" ← if UI Design gate checked → run it
- "I'll dispatch forge for UI work without DESIGN.md" ← WRONG

## References

- `references/pipeline-operations.md` — Gate checklist, execution details, context envelope template
- `references/subagent-prompts.md` — Prompt templates for forge, sentinel, prism dispatch
- `skills/research/references/dispatch-templates.md` — Research subagent dispatch templates

Plan authority lives in `plan-state.json` and `workflow-state.json`. The agent-readable brief exports to `<output_dir>/plan-brief.md`.
