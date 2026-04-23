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
| `scout` | sonnet | Web research, docs lookup, tech comparison | Research |
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
Research (scout, Sonnet) -- if external info needed
  Search docs, APIs, best practices, comparisons
  Output: research report -> feeds into oracle
       |
       v
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
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>
```

Valid transitions:
```
idle -> research     (external info needed before planning)
research -> plan     (research complete)
idle -> plan         (user requests feature, no research needed)
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
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 2: Research (if needed)

Skip for: tasks that only involve the local codebase, internal refactoring, or when the user already has all necessary external context.

Invoke scout when:
- The task involves a library, framework, or API not yet in the codebase
- The user asks to research or look up something
- Technology comparison or evaluation is needed
- Best practices or migration guides need to be found
- Version compatibility or deprecation concerns exist

```
Agent({
  name: "researcher",
  subagent_type: "claude-code-flow:scout",
  model: "sonnet",
  prompt: """
  Research topic: [specific question or area]
  Context: [task description and what we're trying to build]
  What we need: [specific information gaps to fill]
  """
})
```

scout produces a research report. The orchestrator feeds key findings into oracle's planning prompt.

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 3: Plan Gate

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

## Step 4: Design Gate (if needed)

Skip for: bug fixes, small features, build/CI tasks.

For new systems or architectural changes:
1. Spawn **atlas** (Opus) with approved plan as context
2. atlas produces: module design, API surface, data layout, file structure
3. Present to user for confirmation
4. Wait for approval

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase design
```

After approval, atlas appends architecture decisions to `phase-context.md`.

## Step 5: Implementation

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
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
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-tasks <done> <total>
```

## Step 6: Review Gate

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase review
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

## Step 7: Error Recovery

When an agent fails or produces unexpected output:

1. **Agent timeout/crash**: Retry once with the same prompt. If it fails again, report to the user.
2. **Invalid output format**: Re-prompt the agent with explicit format requirements and an example of the expected output structure.
3. **Wrong phase transition**: Check `.claude/flow/workflow-state.json` for the current phase. If an agent is invoked in the wrong phase, halt and report.
4. **Context loss between phases**: Before each phase transition, write a summary to `.claude/flow/phase-context.md` so the next agent has continuity.

**Retry logic:**
- Max 1 retry per agent invocation
- On retry, prepend: "Previous attempt failed. Error was: [error]. Please try again, ensuring [requirement]."
- If retry also fails, escalate to user with: "Agent [name] failed twice on [task]. Error: [error]. Options: retry manually, skip this step, or cancel."

## Step 8: Documentation (optional)

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

## Step 9: Report & Done

Write final state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase idle
```

Present final summary to user with:
- What was implemented
- Files created/modified
- Test results
- Review outcome
- Documentation generated (if applicable)

## Prompting Guidelines

For all agents, include: Context, Scope, Constraints, Dependencies, Output.

For **scout**: also specify research topic, what info gaps need filling, and how findings feed into planning.
For **oracle**: also specify complexity level, HTML requirement, and any research findings from scout.
For **sentinel**: also specify files to review, plan path, focus areas.
For **chronicler**: also specify doc style and target audience.
