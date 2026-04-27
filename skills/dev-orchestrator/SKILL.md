---
name: Dev Orchestrator
version: "2.1.0"
description: This skill should be used when the user asks to "develop a feature", "implement a system", "design architecture", "build an API", "refactor a module", or any multi-step development task that benefits from agent orchestration and model-tiered delegation. Triggers on complex development tasks where planning, implementation, testing, and review should be coordinated.
---

# Development Orchestrator

Orchestrate tasks through Plan -> Implement -> Review pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and dynamic error recovery.

## Common Rationalizations — Reality Check

| Rationalization | Reality |
|---|---|
| "This is simple enough to skip planning" | Simple tasks have hidden complexity. The 2-minute plan saves 20-minute rework. |
| "I can just implement this directly" | Direct implementation without review misses edge cases. Use the pipeline. |
| "The review will slow us down" | Review catches 40%+ of bugs before they compound. Skipping it is false speed. |
| "This subagent can figure out the context" | Subagents build no context from nothing. Construct their prompt precisely. |
| "The user won't want to approve this" | Gates exist because agents miss things humans catch. Present the gate. |
| "I already know what they need" | What you know and what the user needs are not always the same. Ask, don't assume. |

## Agent Roster

| Agent | Model | Role | Gate |
|-------|-------|------|------|
| `scout` | sonnet | Web research, docs lookup, tech comparison | Research |
| `oracle` | opus | Implementation planning, HTML visualization | Plan |
| `atlas` | opus | Architecture design, module decomposition | Design |
| `designer` | sonnet | UI/UX interaction design documents | UI Design |
| `forge` | sonnet | Code implementation (backend, general) | -- |
| `weaver` | sonnet | Frontend implementation (React/Vue/Svelte) | -- |
| `prism` | sonnet | Test frameworks, benchmarks | -- |
| `anvil` | haiku | Build, CI/CD, dependencies | -- |
| `sentinel` | sonnet | Code review before commit | Review |
| `chronicler` | sonnet | Documentation, changelogs, API docs | -- |

## Mode Selection

| Mode | When | Research | Design | Plan Approval | Review | Auto-retry |
|------|------|----------|--------|---------------|--------|------------|
| **quick** | Bug fix, single file, config | No | No | No | Optional | No |
| **standard** | Feature, multi-file change | If needed | No (Yes for UI) | Yes | Yes | No |
| **deep** | New system, architecture refactor | Yes | Yes | Yes (HTML) | Yes | Yes |
| **autonomous** | User gives goal, full delivery | Auto | Auto | Auto | Auto (max 3) | Yes |

Auto-recommend: 1-2 subtasks single domain → quick; 3-5 subtasks → standard; 6+ or cross-module → deep; "just ship it" → autonomous.

Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>`

## Pipeline

```
Mode Selection → Research (scout, if needed) → Plan Gate (oracle)
  → Design Gate (atlas, deep/autonomous only)
  → UI Research (scout, frontend-ui only) → UI Design Gate (designer)
  → Implementation (forge/weaver + prism + anvil, DAG-scheduled)
  → Review Gate (sentinel) → Documentation (chronicler, if needed) → Done
```

## State Machine

Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>`

Key files: `workflow-state.json` (phase/mode/tasks), `phase-context.md` (approved plan + architecture + design), `plan-brief.md` (agent-ready task breakdown from oracle), `ui-research.md` (design research), `modified-files.txt` + `modified-files.jsonl` (file tracking), `review-result.txt` (review outcome), `task-graph.json` (DAG structure).

Phase handoff: each gate agent appends its output to `phase-context.md` with YAML frontmatter. Oracle also writes `plan-brief.md` after approval — this is the agent-consumable version with concrete tasks and file lists.

## Steps

### 1. Analyze + Mode Select
Classify: domain, complexity (1-2 vs 3+ subtasks), needs design/research? Select mode, set phase to `plan`.

### 2. Research (if needed)
Skip for quick mode or internal-only tasks. Invoke scout for external info (library docs, API refs, tech comparisons). Set phase to `plan`.

### 3. Plan Gate
- **quick**: Skip or 2-line inline plan.
- **standard**: oracle produces text summary → user approval.
- **deep**: oracle produces HTML visualization → browser review.
- **autonomous**: oracle produces plan → auto-approve.

Oracle writes summary to `phase-context.md` and generates `task-graph.json`.

### 4. Design Gate (deep/autonomous only)
Skip for quick/standard, bug fixes, small features. Atlas produces module design, API surface, data layout → user approval → append to `phase-context.md`.

### 4a. UI Research (frontend-ui only)
Skip for non-UI tasks or quick mode. Scout researches: similar product patterns (2-3), design trends, best practices, anti-patterns. Produces structured report → saved to `ui-research.md`. Orchestrator extracts reusable knowledge to persistent memory. Appends 3-5 bullet summary to `phase-context.md`.

### 4b. UI Design Gate (frontend-ui, standard+)
Designer produces UI/UX design document based on plan + research → user approval → append to `phase-context.md`. Weaver tasks depend on designer completion in DAG. Standard mode: designer produces a lightweight spec (design direction + component list + key states). Deep/autonomous: full spec with all states, color system, typography, responsive.

### 5. Implementation (DAG-Aware)
Set phase to `impl`. For standard/deep/autonomous: use `task-graph.json` DAG. `task-graph.py get-ready` returns ready tasks. Group by agent, spawn in parallel (max 2). On completion: `set-status <id> done`, update progress. **quick mode**: direct single forge/weaver call.

Parallel rules: forge+prism can parallel (tests on existing code); anvil can parallel with prism; shared file dependencies must NOT parallel. Agent routing: frontend-ui → weaver, everything else → forge.

Context management: after every 3 tasks, generate intermediate summary. Write key decisions to `phase-context.md` incrementally.

### 6. Review Gate
Set phase to `review`. **quick**: optional. **standard/deep**: mandatory sentinel. **autonomous**: auto-invoke, auto-handle feedback.

Outcomes: APPROVE → proceed; REQUEST CHANGES → back to implementer (max 3 rounds); NEEDS DISCUSSION → escalate to user.

For frontend tasks, prism should use browser automation (Playwright/Puppeteer/MCP tools) to capture screenshots and verify DOM elements, styles, and responsive layout against the design spec. Sentinel review should also check visual correctness if automated screenshots are available.

**Canopy Browser Integration:** When running in Canopy, after weaver starts the dev server, open the URL in Canopy's built-in browser for visual verification. Canopy's element capture and screenshots feed directly into agent context, enabling real-time visual review without external browser automation tools. Use device emulation presets for responsive checking.

### 7. Error Recovery
```
syntax error     → auto-correct, retry
dependency error → install missing dep, retry
logic error      → investigate, then fix or escalate
environment error → escalate to user
unknown          → investigate (max 2 retries), then escalate
```

Max 2 retries per task. Always escalate after that.

### 8-9. Documentation + Report
Invoke chronicler if: new public APIs, user requested docs, or existing docs/ directory. Set phase to `idle`. Present final summary with files modified, test results, review outcome.

### 10. Self-Evolution Check
After every workflow completion, check `.claude/flow/evolution-pending.md` for existing proposals and `.claude/flow/evolution.json` config.

**If `EVOLUTION_PENDING` or `EVOLUTION_READY` notification appeared in SessionStart:**

1. Read `.claude/flow/evolution.json` — if `disabled: true`, skip entirely.

2. If no pending proposals but analysis is due (sessions since last analysis >= `auto_analyze_after`):
   - Invoke evolver agent to analyze logs and generate proposals:
     ```
     Agent({ name: "evolver", subagent_type: "claude-code-flow:evolver", model: "opus",
       prompt: "Analyze workflow execution logs and propose prompt improvements. Write proposals to .claude/flow/evolution-pending.md" })
     ```

3. Read `.claude/flow/evolution-pending.md` and present each proposal to the user with:
   - Agent/file affected, specific change (before/after), expected effect, risk level
   - Options: **Approve** / **Reject** / **Defer**

4. For each approved proposal:
   - Run `python hooks/scripts/eval-gate.py validate-prompt-change <agent_file>`
   - PASS → apply the change; WARN → confirm with user; FAIL → skip
   - Update `evolution.json`: set `last_analysis_session_count` to current workflow_stop count
   - Move applied proposals to `.claude/flow/evolution-history.md`
   - If `auto_apply_low_risk: true` and risk is "low", apply without asking

**User control:** Edit `.claude/flow/evolution.json` to configure frequency, disable, or auto-apply. Edit `.claude/flow/evolution-pending.md` to manually modify or reject proposals.

## Verification

**IRON LAW: NEVER claim a phase is complete without fresh verification evidence.**

- "Tests pass" requires actual test output, not "I wrote the tests"
- "Build succeeds" requires actual build output, not "it should compile"
- "Implementation matches plan" requires line-by-line comparison
- "Review passed" requires sentinel APPROVE report

Review is two-stage: Stage 1 spec compliance (did they build the right thing?) → Stage 2 code quality (did they build it right?). NEVER run Stage 2 before Stage 1 passes.

## Subagent Prompt Construction

Subagents get fresh context — they never inherit session history. YOU must give them everything they need:
1. **NEVER let a subagent read the plan file themselves.** Paste relevant sections directly.
2. **Include a "Questions?" gate** — tell subagent to ask before starting work.
3. **Specify output format** — what you expect back (status + deliverables).
4. **Include: Context, Scope, Constraints, Dependencies, Output.**
