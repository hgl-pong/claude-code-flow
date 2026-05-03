---
name: Dev Orchestrator
version: "3.0.0"
description: "Triggers on complex development tasks requiring multi-step orchestration with specialized agents."
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and error recovery.

## Communication Style

Keep user-facing updates and final reports concise. Report outcomes, changed files, verification, and blockers. Avoid explaining the whole pipeline unless the user asks. For routine successful work, use 3-6 bullets or 1-2 short paragraphs.

## Mode Selection

Auto-recommend: 1-2 subtasks single domain → **quick**; 3-5 subtasks → **standard**; 6+ or cross-module → **deep**; "just ship it" → **autonomous**; `ulw`/`ultrawork` → **ultrawork** (use ultrawork skill); `uli` → **uli** (use ultrawork skill ULI branch).

| Mode | Research | Architecture (atlas) | UI Research (scout) | UI Design (designer) | Plan Approval | Review | Auto-retry |
|------|----------|---------------------|--------------------|--------------------|---------------|--------|------------|
| quick | No | No | No | No | No | Optional | No |
| standard | If needed | If needed | Yes for UI tasks | Yes for UI tasks | Yes | Yes | No |
| deep | Yes | Yes | Yes for UI tasks | Yes for UI tasks | Yes (MD) | Yes | Yes |
| autonomous | Auto | Auto | Auto for UI tasks | Auto for UI tasks | Auto | Auto (max 3) | Yes |

"If needed" means: evaluate the condition. If the condition is true, the gate is MANDATORY, not optional.

If user explicitly asks to skip a gate, respect that and record the risk.

Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>`

## Agent Roster

| Agent | Model | Effort | Role | Gate |
|-------|-------|--------|------|------|
| `scout` | sonnet | medium | Web research, docs lookup | Research |
| `oracle` | opus | xhigh | Implementation planning, HTML viz | Plan |
| `atlas` | opus | xhigh | Architecture design | Design |
| `designer` | sonnet | high | UI/UX design documents | UI Design |
| `pd` | sonnet | medium | Product Manager (ULI only) | ULI |
| `forge` | sonnet | high | Code implementation (backend/general) | -- |
| `weaver` | sonnet | high | Frontend implementation | -- |
| `prism` | sonnet | high | Test frameworks, benchmarks | -- |
| `anvil` | haiku | default | Build, CI/CD, dependencies | -- |
| `sentinel` | sonnet | high | Code review | Review |
| `validator` | haiku | default | Functional acceptance testing | Acceptance |
| `chronicler` | haiku | default | Documentation, changelogs | -- |

## Task Domain Detection

Before entering the pipeline, classify the task into a domain. This determines which gates are mandatory.

**Frontend-UI task** — ANY of these conditions is true:
- Task creates or modifies `.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, `.html` files
- Task involves UI components, pages, layouts, styling, or visual elements
- Task mentions "design", "UI", "frontend", "component", "page", "layout", "responsive"
- Task involves user-facing interaction (forms, buttons, navigation, modals)
- Task output will be seen by end users

**Backend task** — ANY of these:
- Task creates or modifies API endpoints, database queries, server logic
- Task involves `.py`, `.go`, `.rs`, `.java`, `.rb`, `.ts` (non-frontend) files
- Task mentions "API", "database", "server", "auth", "backend"

**Cross-domain** — BOTH frontend and backend conditions are true.

If cross-domain: treat each subtask according to its own domain. The pipeline runs ALL applicable gates.

## Mandatory Gate Checklist

After mode selection, use this checklist to determine which gates MUST run. Check EVERY item. If a gate is marked mandatory, it is NOT optional — it MUST complete before proceeding.

```
GATE CHECKLIST (evaluate for this specific task):

[ ] Gate 1: Brainstorm — mandatory for: new features, behavior changes, UI work,
    architecture changes, broad refactors. Skip only for: narrow bug fixes with
    known root cause, config changes, single-file edits with clear spec.

[ ] Gate 2: Research (scout) — see mode table above. If mandatory: scout MUST
    produce findings before plan gate.

[ ] Gate 3: Plan (oracle) — ALWAYS mandatory for standard/deep/autonomous.
    Oracle MUST produce plan-brief.md with TaskCreate tasks.

[ ] Gate 4: Architecture (atlas) — see mode table above. If mandatory: atlas
    MUST produce design document before implementation.

[ ] Gate 5: UI Research (scout) — mandatory when task domain is frontend-UI
    AND mode is standard+. Scout MUST produce ui-research.md.

[ ] Gate 6: UI Design (designer) — mandatory when task domain is frontend-UI
    AND mode is standard+. Designer MUST produce DESIGN.md before weaver
    can be dispatched.

[ ] Gate 7: Review (sentinel) — see mode table above. If mandatory: sentinel
    MUST approve before acceptance.

[ ] Gate 8: Acceptance (validator) — mandatory for standard/deep/autonomous.
    Validator MUST accept before completion.

EXECUTION RULE: After evaluating this checklist, you MUST execute gates in
order (1→2→3→4→5→6→7→8), skipping only gates that are unchecked. You MAY NOT
skip a checked gate. You MAY NOT reorder gates.
```

## Pipeline

```
1. Skill Check → 2. Mode Select → 3. Domain Detect → 4. Gate Checklist
→ 5. Brainstorm Gate (if checked) → 6. Research Gate (if checked)
→ 7. Plan Gate (if checked) → 8. Architecture Gate (if checked)
→ 9. UI Research Gate (if checked) → 10. UI Design Gate (if checked)
→ 11. Implementation → 12. Review Gate (if checked)
→ 13. Acceptance Gate (if checked) → 14. Documentation → Done
```

## State Machine

Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>`

Key files: `workflow-state.json` (phase/mode/tasks), `phase-context.md` (approved plan + design), `plan-brief.md` (agent-ready tasks from oracle), `ui-research.md`, `DESIGN.md`, `modified-files.txt`, `verification-evidence.jsonl` + `last-verification.json`, `review-result.txt`.

Phase handoff: each gate agent appends output to `phase-context.md`. Oracle writes `plan-brief.md` after approval.

## Steps

### 1. Analyze + Mode Select + Domain Detect
Start with `using-claude-code-flow`. Classify: domain (using Task Domain Detection rules), complexity, needs design/research? Select mode, set phase to `plan`.

For new features, behavior changes, UI work, architecture changes, or broad refactors, run `brainstorming` first. Save substantial specs to `docs/superpowers/specs/`.

### 2. Evaluate Gate Checklist
Run the Mandatory Gate Checklist above. Record which gates are mandatory in `phase-context.md` under a `## Gate Checklist` section. Example:
```
## Gate Checklist
- [x] Brainstorm — new feature
- [x] Research — deep mode
- [x] Plan — deep mode
- [x] Architecture — deep mode
- [x] UI Research — frontend-UI task
- [x] UI Design — frontend-UI task
- [x] Review — deep mode
- [x] Acceptance — deep mode
```

This section is the execution contract. You MAY NOT skip a checked gate.

### 3. Brainstorm Gate (if checked)
Run `brainstorming` skill. Output approved design to `phase-context.md`.

### 4. Research Gate (if checked)
Invoke scout for external info. Output to `phase-context.md`.

### 5. Plan Gate (if checked)
- **standard**: oracle markdown plan → user approval.
- **deep**: oracle markdown plan → user approval. (Use HTML visualization only when user explicitly requests it.)
- **autonomous**: oracle plan → auto-approve.

Oracle writes summary to `phase-context.md`. After approval, use `writing-plans` for multi-step work. Oracle creates tasks via TaskCreate with blockedBy dependencies.

### 6. Architecture Gate (if checked)
Atlas produces module design, API surface, data layout → user approval (auto for autonomous) → append to `phase-context.md`.

### 7. UI Research Gate (if checked)
Scout researches similar product patterns, design trends → `ui-research.md`. Extract reusable knowledge. Append summary to `phase-context.md`.

### 8. UI Design Gate (if checked)
Designer produces design document → user approval (auto for autonomous) → append to `phase-context.md`. Also outputs `.claude/flow/DESIGN.md` (structured specs — weaver's input).

After DESIGN.md is written, inform the user:
```
Design viewer available. To review and edit tokens interactively:
  python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/design-server.py
Then open http://localhost:8765 in your browser.
```
If the user edits tokens via the viewer, wait for their confirmation before proceeding to Implementation so DESIGN.md changes are picked up by weaver.

**IRON LAW for UI tasks: weaver MAY NOT be dispatched until DESIGN.md exists.** If DESIGN.md is missing and the task is frontend-UI, STOP and run designer first.

**Hard enforcement for deep mode:** In deep mode with frontend-UI tasks, designer is MANDATORY — no exceptions. Before proceeding to Implementation (step 9), explicitly verify:
1. Task domain includes frontend-UI → YES? → designer MUST have run
2. `.claude/flow/DESIGN.md` exists and is non-empty → YES? → proceed; NO? → STOP, dispatch designer
3. If designer was somehow skipped, DO NOT proceed to Implementation. Go back and run designer now.

### 9. Implementation (Parallel Scheduler + Ralph Loop)
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

Every agent prompt MUST be self-contained. The orchestrator may read files to build the prompt, but the subagent must not be asked to infer missing requirements from a plan file, prior agent output, or chat history. Paste the relevant excerpts directly.

Omitting fields = incomplete dispatch. If a field truly does not apply, write `N/A - <reason>` instead of leaving it blank.

```markdown
## Envelope
- **Goal:** <one-line project goal>
- **Your Task:** <exact task subject from TaskGet>
- **Working Directory:** `<absolute or project-relative cwd>`
- **Completed Dependencies:** <specific outputs now present in git/filesystem>
- **File Scope:** <exact files to create/modify>
- **Test Command:** `<exact command to run for verification>`
- **Acceptance Criteria:** <from task description>
- **Relevant Excerpts:** <requirements/design/code snippets needed to act without reading a separate plan>
- **Constraints:** <project conventions, banned patterns, dependency limits>
- **Out of Scope:** <nearby work the agent must not touch>

## FILES_MODIFIED (required on completion)
List ALL files you created or modified: <path1>, <path2>, ...
```

For implementation agents, append the expected completion schema:

```markdown
## Completion Schema
- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Files modified: <same list as FILES_MODIFIED>
- Verification: `<command>` -> <pass/fail + key output>
- RED/GREEN evidence: <required for behavior changes>
- Concerns: <specific risks, or "none">
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
1. Read its output — verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` declaration against task scope
3. Check verification evidence includes command, status, and key output
4. If behavior changed, confirm RED/GREEN evidence or dispatch prism/forge correction
5. If worktree was used: review changes, merge if clean
6. `TaskUpdate` status=completed only after scope and evidence checks pass
7. Record evidence in `verification-evidence.jsonl`
8. Check if new tasks are now unblocked → dispatch next batch

After every 3 tasks: write key decisions to `phase-context.md`.

### 10. Review Gate (if checked)
Set phase to `review`. Two-stage sentinel review.

**Two-stage review — always in this order:**
1. **Stage 1: Spec Compliance** — does the implementation match the plan? Check every requirement from plan-brief.
2. **Stage 2: Code Quality** — only runs if Stage 1 passes. Check naming, structure, error handling, test coverage.

NEVER reverse the order. If Stage 1 fails, Stage 2 is skipped.

Outcomes: APPROVE→proceed; REQUEST CHANGES→back to implementer (max 3 rounds); NEEDS DISCUSSION→escalate.

For frontend: prism uses browser automation to verify against design spec.

#### Subagent-Driven Review (deep/autonomous mode)

For deep and autonomous modes, dispatch each review stage as a **separate sentinel subagent** for zero context contamination between stages:

1. Dispatch sentinel with `review_focus: spec_compliance` in the context envelope → spec-only review
2. If APPROVE: dispatch a **fresh** sentinel with `review_focus: code_quality` → quality-only review
3. If Stage 1 REQUEST CHANGES: back to implementer (max 3 rounds)

For quick/standard: single sentinel run with both stages (no `review_focus` parameter) — backward compatible.

### 11. Acceptance Gate (if checked)
After sentinel APPROVE, invoke validator. Validator reads `plan-brief.md`, runs build+tests, checks feature delivery.

Outcomes: ACCEPT→TaskUpdate completed; REJECT→back to implementer (max 2 rounds).

### 12. Error Recovery
```
syntax error     → auto-correct, retry
dependency error → install, retry
logic error      → investigate, fix or escalate
environment error → escalate to user
unknown          → investigate (max 2 retries), escalate
```

### 13. Documentation + Report
Invoke chronicler if: new public APIs, user requested docs, or existing docs/ directory. Use `verification-before-completion`. Set phase to `idle`. Present a concise final summary: outcome, files, verification, caveats.

## Verification

**IRON LAW: NEVER claim a phase is complete without fresh verification evidence.**

- "Tests pass" requires actual test output
- "Build succeeds" requires actual build output
- "Implementation matches plan" requires line-by-line comparison
- TaskUpdate status=completed only after validator ACCEPT

Review is two-stage: Stage 1 spec compliance → Stage 2 code quality. NEVER run Stage 2 before Stage 1 passes.

### Red Flags — STOP and re-read the pipeline if you catch yourself:

- "I'll skip review for this small change"
- "The agent output looks fine, I don't need to verify FILES_MODIFIED"
- "I'll carry this context into the next agent dispatch"
- "Stage 1 and Stage 2 can run together"
- "I'll skip the Context Envelope, the agent has enough context"
- "I can skip TaskCreate and just do it inline"
- "This frontend task doesn't need designer" ← WRONG. If Gate Checklist checked UI Design, run it.
- "I can skip designer and go straight to Implementation" ← WRONG. In deep mode with frontend-UI, designer is mandatory — verify DESIGN.md exists before step 9.
- "I'll dispatch weaver without DESIGN.md" ← WRONG. UI Design gate must complete first.

## Subagent Prompt Construction

Subagents are **stateless** — each dispatch is a fresh agent with zero memory of prior tasks. Construct fully self-contained prompts using the Context Envelope:

1. Include the full envelope (Goal, Task, Working Directory, Dependencies, File Scope, Test Command, Acceptance Criteria, Relevant Excerpts, Constraints, Out of Scope)
2. Paste relevant plan/design/code sections directly (never make subagents hunt for requirements in a separate plan)
3. Specify expected output using the Completion Schema
4. Do NOT reference prior agent outputs — summarize durable filesystem/git results instead
