---
name: Dev Orchestrator
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
Report & Done
```

## Step 1: Analyze

Classify the task:
- **Domain**: What area of the codebase is affected
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
- **Needs design**: Yes (new system) vs No (bug fix, feature addition)

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

## Step 3: Design Gate (if needed)

Skip for: bug fixes, small features, build/CI tasks.

For new systems or architectural changes:
1. Spawn **atlas** (Opus) with approved plan as context
2. atlas produces: module design, API surface, data layout, file structure
3. Present to user for confirmation
4. Wait for approval

## Step 4: Implementation

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

## Step 5: Review Gate

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
- APPROVE -> report
- REQUEST CHANGES -> fixes to forge -> re-review
- NEEDS DISCUSSION -> present to user

Max 3 review rounds. Escalate to user after that.

## Prompting Guidelines

For all agents, include: Context, Scope, Constraints, Dependencies, Output.

For **oracle**: also specify complexity level and HTML requirement.
For **sentinel**: also specify files to review, plan path, focus areas.
