---
name: Dev Orchestrator
version: "2.1.0"
description: "Orchestrate multi-step development through Brainstorm→Plan→Design→Implement→Review→Acceptance pipeline with model-tiered agents. Triggers on complex development tasks."
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and error recovery.

## Mode Selection

Auto-recommend: 1-2 subtasks single domain → **quick**; 3-5 subtasks → **standard**; 6+ or cross-module → **deep**; "just ship it" → **autonomous**; `ulw`/`ultrawork` → **ultrawork** (use ultrawork skill); `uli` → **uli** (use ultrawork skill ULI branch).

| Mode | Research | Design | Plan Approval | Review | Auto-retry |
|------|----------|--------|---------------|--------|------------|
| quick | No | No | No | Optional | No |
| standard | If needed | No (Yes for UI) | Yes | Yes | No |
| deep | Yes | Yes | Yes (HTML) | Yes | Yes |
| autonomous | Auto | Auto | Auto | Auto (max 3) | Yes |

If user explicitly asks to skip a gate, respect that and record the risk.

Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>`

## Agent Roster

| Agent | Model | Role | Gate |
|-------|-------|------|------|
| `scout` | sonnet | Web research, docs lookup | Research |
| `oracle` | opus | Implementation planning, HTML viz | Plan |
| `atlas` | opus | Architecture design | Design |
| `designer` | sonnet | UI/UX design documents | UI Design |
| `pd` | sonnet | Product Manager (ULI only) | ULI |
| `forge` | sonnet | Code implementation (backend/general) | -- |
| `weaver` | sonnet | Frontend implementation | -- |
| `prism` | sonnet | Test frameworks, benchmarks | -- |
| `anvil` | haiku | Build, CI/CD, dependencies | -- |
| `sentinel` | sonnet | Code review | Review |
| `validator` | sonnet | Functional acceptance testing | Acceptance |
| `chronicler` | sonnet | Documentation, changelogs | -- |

## Pipeline

```
Skill Check → Brainstorm/Design (if creative) → Mode Select → Research (scout, if needed)
→ Plan (oracle) → Design (atlas, deep/autonomous) → UI Research + Design (frontend-ui)
→ Implementation (forge/weaver + prism + anvil, DAG-scheduled)
→ Review (sentinel) → Acceptance (validator) → Documentation (chronicler) → Done
```

## State Machine

Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>`

Key files: `workflow-state.json` (phase/mode/tasks), `phase-context.md` (approved plan + design), `plan-brief.md` (agent-ready tasks from oracle), `ui-research.md`, `modified-files.txt`, `verification-evidence.jsonl` + `last-verification.json`, `review-result.txt`.

Phase handoff: each gate agent appends output to `phase-context.md`. Oracle writes `plan-brief.md` after approval.

## Steps

### 1. Analyze + Mode Select
Start with `using-claude-code-flow`. Classify: domain, complexity, needs design/research? Select mode, set phase to `plan`.

For new features, behavior changes, UI work, architecture changes, or broad refactors, run `brainstorming` first. Save substantial specs to `docs/superpowers/specs/`.

### 2. Research (if needed)
Skip for quick mode or internal-only tasks. Invoke scout for external info.

### 3. Plan Gate
- **quick**: Skip or 2-line inline plan.
- **standard**: oracle text summary → user approval.
- **deep**: oracle HTML visualization → browser review.
- **autonomous**: oracle plan → auto-approve.

Oracle writes summary to `phase-context.md`. After approval, use `writing-plans` for multi-step work. Oracle creates tasks via TaskCreate with blockedBy dependencies.

### 4. Design Gate (deep/autonomous only)
Atlas produces module design, API surface, data layout → user approval → append to `phase-context.md`.

### 4a. UI Research (frontend-ui, standard+)
Scout researches similar product patterns, design trends → `ui-research.md`. Extract reusable knowledge. Append summary to `phase-context.md`.

### 4b. UI Design Gate (frontend-ui, standard+)
Designer produces design document → user approval → append to `phase-context.md`. Also outputs `.claude/flow/DESIGN.md` (structured specs — weaver's input).

### 5. Implementation (DAG-Aware)
Set phase to `impl`. Use TaskList for available tasks. Group by agent type, spawn max 2 in parallel. Apply `testing-strategy` before production code. For bugs with unknown cause, apply `systematic-debugging` first.

Task dependency: use `blockedBy`/`addBlocks`. Frontend tasks blocked by designer via DAG.

Before parallel dispatch: check for overlapping file paths — serialize conflicting tasks.

After every 3 tasks: write key decisions to `phase-context.md`.

### 6. Review Gate
Set phase to `review`. **quick**: optional. **standard/deep**: mandatory sentinel. **autonomous**: auto.

Outcomes: APPROVE→proceed; REQUEST CHANGES→back to implementer (max 3 rounds); NEEDS DISCUSSION→escalate.

For frontend: prism uses browser automation to verify against design spec.

### 7. Acceptance Gate
After sentinel APPROVE, invoke validator. **quick**: optional. **standard/deep**: mandatory. **autonomous**: auto.

Validator reads `plan-brief.md`, runs build+tests, checks feature delivery.

Outcomes: ACCEPT→TaskUpdate completed; REJECT→back to implementer (max 2 rounds).

### 8. Error Recovery
```
syntax error     → auto-correct, retry
dependency error → install, retry
logic error      → investigate, fix or escalate
environment error → escalate to user
unknown          → investigate (max 2 retries), escalate
```

### 9. Documentation + Report
Invoke chronicler if: new public APIs, user requested docs, or existing docs/ directory. Use `verification-before-completion`. Set phase to `idle`. Present final summary.

## Verification

**IRON LAW: NEVER claim a phase is complete without fresh verification evidence.**

- "Tests pass" requires actual test output
- "Build succeeds" requires actual build output
- "Implementation matches plan" requires line-by-line comparison
- TaskUpdate status=completed only after validator ACCEPT

Review is two-stage: Stage 1 spec compliance → Stage 2 code quality. NEVER run Stage 2 before Stage 1 passes.

## Subagent Prompt Construction

Subagents get fresh context — give them everything:
1. Paste relevant plan sections directly (never let subagent read plan file themselves)
2. Include: Context, Scope, Constraints, Dependencies, Output format
3. Specify expected output: status + deliverables
