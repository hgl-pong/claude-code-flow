---
name: Dev Orchestrator
version: "1.1.0"
description: This skill should be used when the user asks to "develop a feature", "implement a system", "design architecture", "build an API", "refactor a module", or any multi-step development task that benefits from agent orchestration and model-tiered delegation. Triggers on complex development tasks where planning, implementation, testing, and review should be coordinated.
---

# Development Orchestrator

Orchestrate tasks through Plan -> Implement -> Review pipeline with model-tiered agents.

## Agent Roster

| Agent | Model | Role | Gate |
|-------|-------|------|------|
| `oracle` | opus | Implementation planning, HTML visualization | Plan |
| `atlas` | opus | Architecture design, module decomposition | Design |
| `forge` | sonnet | Code implementation | -- |
| `prism` | sonnet | Test frameworks, benchmarks | -- |
| `anvil` | haiku | Build, CI/CD, dependencies | -- |
| `sentinel` | sonnet | Code review before commit | Review |
| `chronicler` | sonnet | Documentation, changelogs, API docs | -- |

## Pipeline

All tasks follow this pipeline. Complexity determines which stages activate.

```
Plan Gate (oracle, Opus)
  Complex: HTML viz -> browser review
  Simple:  text summary -> inline approval
  [BLOCKED until user approves]
       |
       v
Design Gate (atlas, Opus) -- only for new systems / arch changes
  [BLOCKED until user approves]
       |
       v
Implementation
  forge + prism + anvil (parallel where possible)
       |
       v
Review Gate (sentinel, Sonnet)
  PASS  -> proceed
  FAIL  -> back to forge -> re-review (max 3 rounds)
  [BLOCKED until review passes]
       |
       v
Documentation (chronicler, Sonnet) -- if needed
       |
       v
Report & Done
```

## State Machine

Workflow phases follow strict transition rules. Write state to `.claude/flow/workflow-state.json` at each transition using:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase <phase>
```

Valid transitions:
```
idle -> plan         (user requests feature)
plan -> design       (plan approved, needs architecture)
plan -> impl         (plan approved, no architecture needed)
design -> impl       (design approved)
impl -> review       (implementation complete)
review -> impl       (review failed, back to forge)
review -> idle       (review passed, done)
impl -> idle         (simple task, skip review)
* -> idle            (user cancels or error)
```

Invalid transitions (must reject):
```
idle -> impl         (no plan approved)
plan -> review       (no implementation yet)
design -> review     (no implementation yet)
```

## Context Preservation

Between phases, write context files to maintain continuity:

| File | Written by | Read by | Content |
|------|-----------|---------|---------|
| `.claude/flow/workflow-state.json` | flow-state.sh | statusline, orchestrator | Current phase, task progress |
| `.claude/flow/phase-context.md` | oracle/atlas | forge/sentinel | Approved plan summary, architecture decisions |
| `.claude/flow/modified-files.txt` | track-changes.sh | sentinel | Files modified during implementation |
| `.claude/flow/review-result.txt` | sentinel | orchestrator | Latest review outcome |

**Phase handoff protocol:**
1. After plan approval: oracle writes plan summary to `phase-context.md`
2. After design approval: atlas appends architecture decisions to `phase-context.md`
3. Before review: orchestrator lists modified files for sentinel
4. After review: sentinel writes outcome to `review-result.txt`

## Step 1: Analyze

Classify the task:
- **Domain**: What area of the codebase is affected
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
- **Needs design**: Yes (new system) vs No (bug fix, feature addition)

Write initial state:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase plan
```

## Step 2: Plan Gate

Always invoke oracle. Output differs by complexity.

**Complex** (new system, multi-module, architectural):
- oracle generates self-contained HTML (inline CSS/JS, dark theme, no external deps)
- Include: architecture overview, phase timeline, dependency graph, risk table, file tree
- Save to temp file, open in browser, wait for feedback, iterate until approved

**Simple** (bug fix, single feature, config):
- oracle produces text summary: what to change, which files, risks
- Present inline for quick approval

**Do NOT proceed until user approves the plan.**

After approval, oracle writes plan summary to `.claude/flow/phase-context.md`.

## Step 3: Design Gate (if needed)

Skip for: bug fixes, small features, build/CI tasks.

For new systems or architectural changes:
1. Spawn **atlas** (Opus) with approved plan as context
2. atlas produces: module design, API surface, data layout, file structure
3. Present to user for confirmation
4. Wait for approval

Write state:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase design
```

After approval, atlas appends architecture decisions to `phase-context.md`.

## Step 4: Implementation

Write state:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase impl
```

**Simple mode** (1-3 subtasks) — direct Agent tool calls:

```
Agent({ name: "dev", subagent_type: "claude-code-flow:forge", model: "sonnet", prompt: "..." })
```

**Complex mode** (4+ subtasks) — Team + TaskList:

```
TeamCreate({ team_name: "feature-x" })
TaskCreate({ subject: "...", addBlockedBy: [...] })
Agent({ name: "dev-1", team_name: "...", subagent_type: "claude-code-flow:forge", model: "sonnet", prompt: "..." })
```

**Parallel rules:**
- forge + prism can parallel if tests are for existing code
- anvil can parallel with prism
- atlas always before forge

Update task progress:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-tasks <done> <total>
```

## Step 5: Review Gate

Write state:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase review
```

Always invoke sentinel after implementation:

```
Agent({
  name: "reviewer",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
  Task: [task description]
  Plan reference: [path to approved plan]
  Files created: [list]
  Files modified: [list]
  Focus areas: [specific concerns]
  """
})
```

**Outcomes:**
- APPROVE -> write result to `.claude/flow/review-result.txt`, proceed
- REQUEST CHANGES -> fixes to forge -> re-review
- NEEDS DISCUSSION -> present to user

Max 3 review rounds. Escalate to user after that.

## Step 6: Error Recovery

When an agent fails or produces unexpected output:

1. **Agent timeout/crash**: Retry once with the same prompt. If it fails again, report to the user.
2. **Invalid output format**: Re-prompt the agent with explicit format requirements and an example of the expected output structure.
3. **Wrong phase transition**: Check `.claude/flow/workflow-state.json` for the current phase. If an agent is invoked in the wrong phase, halt and report.
4. **Context loss between phases**: Before each phase transition, write a summary to `.claude/flow/phase-context.md` so the next agent has continuity.

**Retry logic:**
- Max 1 retry per agent invocation
- On retry, prepend: "Previous attempt failed. Error was: [error]. Please try again, ensuring [requirement]."
- If retry also fails, escalate to user with: "Agent [name] failed twice on [task]. Error: [error]. Options: retry manually, skip this step, or cancel."

## Step 7: Documentation (optional)

After implementation passes review, invoke chronicler if:
- The feature adds new public APIs
- The user requested documentation
- The project has a docs/ directory with existing documentation

```
Agent({
  name: "doc-writer",
  subagent_type: "claude-code-flow:chronicler",
  model: "sonnet",
  prompt: """
  Generate documentation for the completed feature.
  Plan reference: [path to approved plan]
  Files created: [list]
  Files modified: [list]
  Doc style: match existing docs in [docs/ or README.md]
  """
})
```

## Step 8: Report & Done

Write final state:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.sh set-phase idle
```

Present final summary to user with:
- What was implemented
- Files created/modified
- Test results
- Review outcome
- Documentation generated (if applicable)

## Prompting Guidelines

For all agents, include: Context, Scope, Constraints, Dependencies, Output.

For **oracle**: also specify complexity level and HTML requirement.
For **sentinel**: also specify files to review, plan path, focus areas.
For **chronicler**: also specify doc style and target audience.
