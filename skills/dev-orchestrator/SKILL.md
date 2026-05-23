---
name: Dev Orchestrator
version: "5.0.0"
description: "Orchestrate dev work: implement, build, fix, refactor, test, review, ship, verify, finish branches, coordinate agents."
when_to_use: "Trigger on 'implement', 'build', 'fix', 'refactor', 'ship', 'execute plan', 'multi-step', 'cross-file change', 'finish branch'."
argument-hint: "<task description, approved plan, feature, fix, refactor, or delivery goal>"
---

# Development Orchestrator

Orchestrate tasks through the development pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and error recovery. Also serves as the **workflow entry point** — routes tasks to specialized skills when they don't belong in the main pipeline.

<SUBAGENT-STOP>
If dispatched as a subagent to execute a specific task, skip the routing section below and go directly to Pipeline Steps.
</SUBAGENT-STOP>

## Entry Routing

Use this section as a **single routing pass** when no command, hook, or active skill has already selected the path.

### De-Dupe Guard

Do not re-evaluate routing when any of these is true:

- A slash command (`/plan`, `/brainstorm`, `/write-plan`, `/execute-plan`, `/quick-fix`) already matched.
- A hook already says `Primary skill:` or routes to a specific workflow skill.
- You are already inside an active skill's flow.
- The task is an approved plan/spec moving into execution.

Built-in plan guard: avoid `EnterPlanMode`. Use `/plan` instead. If the user asks for "plan mode", prefer `plan`.

### Instruction Priority

1. **User's explicit instructions** (CLAUDE.md, direct requests) — highest
2. **Plugin skills** — override default behavior where they conflict
3. **Default system prompt** — lowest

### Skill Selection

| Situation | Route to |
|---|---|
| `ulw` or `ultrawork` in prompt | `ultrawork` — full autonomous delivery |
| `uli` in prompt | `ultrawork` (ULI branch) — product iteration loop |
| Ambiguous new feature, substantial behavior change, UI/architecture decision, broad refactor | `brainstorming`, then `planning` if execution needs a task plan |
| Task primarily asks for a proposal, plan, sequencing, or approval gate | `planning` |
| Task references another repo/plugin/workflow as inspiration or source material | `workflow-intake` before planning |
| Implement, build, fix, refactor, ship, deliver, or execute | This skill (continue below) |
| Multi-step implementation, approved plan, cross-file change | This skill (continue below) |
| Bug or failing behavior with unknown cause | `systematic-debugging` |
| Any production code change | `testing-strategy` with TDD cycle |
| Code review request or quality evaluation | `code-review` |
| Design feedback, handoff, system audit | `design` |
| Architecture decision, deploy checklist, incident, tech debt | `engineering-ops` |
| Research, library evaluation, user research | `research` |
| Plan or design already approved, need execution | This skill (continue below) |
| Implementation complete, tests pass | This skill → Finish Branch phase |

### Skill Priority

When multiple skills apply:

1. **Primary route first** — choose one owner.
2. **Process skills second** — `brainstorming`, `systematic-debugging` only when trigger conditions met.
3. **Implementation skills third** — `testing-strategy` and this skill for code delivery.
4. **Verification last** — verification gate before final delivery (see `references/verification-gate.md`).

## Trigger Bias

Default to this skill whenever the user is asking to **do the work**, not merely discuss it. If a request includes implementation, execution, feature delivery, fixing, refactoring, testing handoff, review handoff, multi-file edits, multiple subtasks, or "finish/ship/deliver this", this skill should be considered active.

Strong trigger phrases:

- "execute the plan", "implement this", "build this", "ship it", "deliver end-to-end"
- "multi-step", "multiple files", "full-stack", "cross-domain", "coordinate agents"
- "run the pipeline", "orchestrate", "plan then implement", "fix and verify"
- "after approval", "use forge/prism/sentinel", "handoff to agents"

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

Research is dispatched as **general-purpose subagents** using the `research` skill methodology. No dedicated agent needed — see `skills/research/references/dispatch-templates.md`. **NEVER use `subagent_type: "claude-code-flow:research"` — always use `subagent_type: "general-purpose"` with research methodology inlined.**

External workflow references are handled by the `workflow-intake` skill before oracle planning. They are source material, not authority. Intake must strengthen the existing pipeline and must not create a competing surface.

## Pipeline Steps

### 1. Analyze + Mode + Domain

Classify domain (frontend-UI / backend / cross-domain), complexity, and mode. For new ambiguous features or substantial design decisions, run `brainstorming` first; skip it for approved specs/plans, narrow fixes, direct execution, and routine maintenance. If the request references another repo, agent pack, plugin, or workflow, run `workflow-intake` before oracle planning.

### 2. Evaluate Gates → 3-8. Execute Gates

See `references/pipeline-operations.md` for full gate checklist and execution details. Record in `<output_dir>/phase-context.md`.

Key rules:
- **Gate 2a: Reference Intake → Plan Gate**: mandatory when referencing external repos/plugins/workflows. Inspect selectively, record Adopt/Adapt/Reject/Defer in `intake-decision.md`.
- **Research Gate → Plan Gate**: research subagent and oracle are STRICTLY SEQUENTIAL. Never dispatch in parallel.
- **Plan Gate**: oracle creates plan-brief.md + TaskCreate with blockedBy
- **Plan Review Gate**: ALWAYS mandatory — oracle self-reviews plan, then user reviews and approves before execution
- **UI Design Gate**: self-review → design viewer (optional) → user approval before forge dispatch
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

For 3+ subtasks: see `references/parallel-dispatch.md` for batch grouping and conflict isolation.

### 10-11. Review + Acceptance

Two-stage sentinel review, then prism acceptance. See `references/pipeline-operations.md`.

### 12. Verification Gate

**NEVER claim completion without fresh verification evidence.** See `references/verification-gate.md` for the full gate function and evidence standards.

### 13. Finish Branch

When implementation is complete and tests pass, guide branch completion. See `references/finish-branch.md` for the full process: verify tests → detect environment → present options → execute → cleanup.

### 14. Report

Concise: outcome, files changed, verification, caveats.

## Red Flags — STOP

- "I'll skip review for this small change"
- "The agent output looks fine, I don't need to verify FILES_MODIFIED"
- "I'll carry this context into the next agent dispatch"
- "This external workflow is popular, so I'll import its agents/commands wholesale"
- "Stage 1 and Stage 2 can run together"
- "This frontend task doesn't need ui-design skill" ← if UI Design gate checked → run it
- "I'll dispatch forge for UI work without DESIGN.md" ← WRONG
- "Should work now" / "Probably fine" / "Seems to pass" ← NOT EVIDENCE

## Response Style

Concise. Lead with the result. Include only decisions, files, commands, risks, and next steps. Default: 3-6 bullets or 1-2 short paragraphs.

**ULW exception:** In `ultrawork` mode approval gates are bypassed; verification evidence and test-first are still mandatory.

## References

- `references/pipeline-operations.md` — Gate checklist, execution details, context envelope template
- `references/subagent-prompts.md` — Prompt templates for forge, sentinel, prism dispatch
- `references/parallel-dispatch.md` — File conflict analysis, parallel limits, decomposition patterns, inter-agent handoff
- `references/verification-gate.md` — Verification gate function, evidence standards, rationalization prevention
- `references/finish-branch.md` — Branch completion: merge, PR, keep, discard
- `references/diagnostics.md` — Diagnostic runtime files, metrics commands, output rules
- `references/review.md` — Review command boundaries, sentinel inputs, fix loops
- `skills/research/references/dispatch-templates.md` — Research subagent dispatch templates

Plan authority lives in `plan-state.json` and `workflow-state.json`. The agent-readable brief exports to `<output_dir>/plan-brief.md`.
