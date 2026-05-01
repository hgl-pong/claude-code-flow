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

### 5. Implementation (Parallel Scheduler + Ralph Loop)
Set phase to `impl`. Apply `testing-strategy` before production code. For bugs with unknown cause, apply `systematic-debugging` first.

#### Ralph Loop (Stateless-Iterative Execution)

Each agent dispatch is **stateless** — the prompt must be fully self-contained. Do NOT carry outputs from agent N into agent N+1. Cross-task dependencies flow through `plan-brief.md` and git state, not through session context.

```
FOR each task batch:
  1. PICK — TaskList → filter pending, unblocked tasks
  2. ANALYZE — extract file paths, build conflict graph
  3. ENVELOPE — construct self-contained prompt for each task
  4. DISPATCH — fire all non-conflicting agents in one message
  5. WAIT — system notifies on completion (do NOT poll/sleep)
  6. VERIFY — check output status + FILES_MODIFIED
  7. RECORD — TaskUpdate + evidence
  8. LOOP — back to step 1 (fresh context, no prior agent output)
```

**Why:** Accumulating agent outputs in session context causes hallucination in later tasks. Each agent gets exactly what it needs — nothing more, nothing less.

#### Parallel Limits

| Agent Type | Max Parallel | Isolation |
|---|---|---|
| forge / weaver (code) | 3 | worktree if file conflict |
| prism (tests) | 2 | worktree if file conflict |
| anvil (build) | 1 | never parallel |

#### File Conflict Analysis

Before dispatching multiple agents simultaneously:
1. Use `TaskGet` on each candidate task to read its description
2. Extract file paths mentioned in "Files:" section or description text
3. If two tasks share any file path → **conflict detected**
4. Conflicting tasks: dispatch with `isolation: "worktree"` (each gets its own branch)
5. Non-conflicting tasks: dispatch without isolation (share worktree)

#### Context Envelope (Required for Every Dispatch)

Every agent prompt MUST contain this envelope. Omitting fields = incomplete dispatch.

```markdown
## Envelope
- **Goal:** <one-line project goal from plan-brief>
- **Your Task:** <exact task subject from TaskGet>
- **Completed Dependencies:** <summary of what blockedBy tasks produced — read git diff or plan-brief>
- **File Scope:** <exact files to create/modify>
- **Test Command:** `<exact command to run for verification>`
- **Acceptance Criteria:** <from task description>
- **Constraints:** <project conventions, banned patterns from plan-brief>

## FILES_MODIFIED (required on completion)
List ALL files you created or modified: <path1>, <path2>, ...
```

#### Agent Dispatch Call

```
Agent({
  description: "<task_subject>",
  subagent_type: "claude-code-flow:<agent>",
  model: "<agent_model>",
  prompt: "<full context envelope + task details>",
  isolation: "<worktree if conflict detected, else omit>",
  run_in_background: true
})
```

**Dispatch all non-conflicting agents in a single message** (multiple Agent calls).

#### Completion Handling

When an agent completes:
1. Read its output — verify status is DONE
2. Check FILES_MODIFIED declaration against task scope
3. If worktree was used: review changes, merge if clean
4. `TaskUpdate` status=completed
5. Record evidence in `verification-evidence.jsonl`
6. Check if new tasks are now unblocked → dispatch next batch

After every 3 tasks: write key decisions to `phase-context.md`.

### 6. Review Gate (Two-Stage)
Set phase to `review`. **quick**: optional. **standard/deep**: mandatory sentinel. **autonomous**: auto.

**Two-stage review — always in this order:**
1. **Stage 1: Spec Compliance** — does the implementation match the plan? Check every requirement from plan-brief.
2. **Stage 2: Code Quality** — only runs if Stage 1 passes. Check naming, structure, error handling, test coverage.

NEVER reverse the order. If Stage 1 fails, Stage 2 is skipped.

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

Subagents are **stateless** — each dispatch is a fresh agent with zero memory of prior tasks. Construct fully self-contained prompts using the Context Envelope:

1. Include the full envelope (Goal, Task, Dependencies, File Scope, Test Command, Acceptance Criteria, Constraints)
2. Paste relevant plan sections directly (never let subagent read plan file themselves)
3. Specify expected output: status + FILES_MODIFIED + deliverables
4. Do NOT reference prior agent outputs — the agent has no access to them
