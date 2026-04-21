---
name: Game Engine Dev
description: This skill should be used when the user asks to "develop a game engine feature", "implement an engine system", "design engine architecture", "add a renderer", "build a physics system", "create an ECS", "set up the build system", "write engine tests", or mentions game engine development tasks involving C++, Lua, HLSL, or CMake. Triggers on any multi-step game engine development task that benefits from agent orchestration and model-tiered delegation.
---

# Game Engine Development Orchestrator

Orchestrate game engine development tasks by analyzing complexity, decomposing work, and delegating to specialized agents with appropriate model tiers. Every complex task follows a **Plan → Review → Implement → Review → Commit** pipeline.

## Agent Roster

| Agent | Model | Role | Color |
|-------|-------|------|-------|
| `game-engine-dev:plan-agent` | opus | Implementation planning, phased roadmap, HTML visualization | cyan |
| `game-engine-dev:architect` | opus | Architecture design, module decomposition, ECS design, performance strategy | magenta |
| `game-engine-dev:core-developer` | sonnet | C++/Lua/HLSL implementation, memory management, concurrency | blue |
| `game-engine-dev:test-engineer` | sonnet | Test frameworks, unit/integration/performance tests | green |
| `game-engine-dev:build-engineer` | haiku | CMake, CI/CD, cross-platform compilation, dependency management | yellow |
| `game-engine-dev:review-agent` | sonnet | Code review before commit, correctness/performance/architecture check | red |

## Orchestration Workflow

### Step 1: Analyze the Task

Read the user's request and classify it by:
- **Domain**: Rendering, Physics, Audio, ECS, Input, Resource Management, Build System, Testing
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting concerns)
- **Phase**: Design, Implementation, Testing, Build/Deploy

### Step 2: Plan (Complex Tasks)

For complex tasks (3+ subtasks, new systems, architectural changes):

1. Spawn the **plan-agent** to create a phased implementation plan
2. Plan-agent generates an HTML visualization and saves to a temp file
3. Open the HTML in the user's browser for review
4. Wait for user feedback before proceeding
5. If user requests changes, iterate with plan-agent until approved

For simple tasks (bug fix, single feature, config change), skip planning and go directly to implementation.

### Step 3: Decompose into Subtasks

Break the approved plan (or simple task) into concrete, assignable subtasks:
- Have a clear deliverable (file, module, test, config)
- Map to exactly one agent
- Be independently verifiable

**Decomposition patterns by domain:**

- **New system/feature** → Plan-agent plans → Architect designs → Core-developer implements → Review-agent reviews → Test-engineer writes tests
- **Bug fix** → Core-developer investigates and fixes → Review-agent reviews → Test-engineer adds regression test
- **Build/CI issue** → Build-engineer handles directly
- **Performance optimization** → Plan-agent plans → Architect analyzes → Core-developer implements → Review-agent reviews → Test-engineer benchmarks
- **Architecture refactor** → Plan-agent plans → Architect designs → Core-developer executes → Review-agent reviews → Test-engineer validates → Build-engineer updates build

### Step 4: Choose Orchestration Mode

**Simple mode** (1-2 subtasks, single domain):
- Use the `Agent` tool directly to spawn agents with explicit `model` parameter
- Sequential execution, results flow back to the conversation

**Complex mode** (3+ subtasks, cross-cutting):
- Use `TeamCreate` to create a team
- Use `TaskCreate` to create tasks with dependencies (`addBlockedBy`)
- Use `Agent` tool with `team_name` to spawn teammates
- Agents self-coordinate via TaskList

### Step 5: Execute with Model Assignment

When spawning agents, always specify the `model` parameter:

```
Agent({
  name: "plan-agent",
  subagent_type: "game-engine-dev:plan-agent",
  model: "opus",
  prompt: "..."
})
```

**Model selection rules:**
- `opus` — For plan-agent and architect: deep reasoning, system design, trade-off analysis, visual planning
- `sonnet` — For core-developer, test-engineer, and review-agent: code generation, test writing, quality review
- `haiku` — For build-engineer: config files, build scripts, CI pipelines (fast, low-cost)

### Step 6: Review Before Commit

After core-developer finishes implementation, **automatically insert a review step**:

1. Spawn **review-agent** with the list of files created/modified
2. Review-agent checks correctness, performance, architecture adherence
3. If review finds critical issues → delegate fixes back to core-developer
4. If review passes → proceed to commit or next phase

The review-agent is a read-only gate — it never modifies code. Fixes go back through the core-developer.

### Step 7: Aggregate and Report

After all agents complete and review passes:
1. Collect results from each agent
2. Verify cross-agent consistency (plan matches implementation matches review)
3. Check that build-engineer's config covers all new files
4. Confirm test-engineer's tests cover core-developer's changes
5. Report summary to user with file-level change list and review status

## Task Prompting Guidelines

When delegating to agents, include in the prompt:
- **Context**: What the overall project goal is
- **Scope**: Exactly what this agent should produce
- **Constraints**: Files to modify, patterns to follow, APIs to use
- **Dependencies**: What other agents are producing (if known)
- **Output**: What the agent should return

For review-agent specifically, include:
- **Files to review**: Explicit list of created/modified files
- **Plan reference**: Path to the plan spec (if available)
- **Focus areas**: Any specific concerns (thread safety, memory, performance)

## Additional Resources

- **`references/architecture-patterns.md`** — Common game engine architecture patterns (ECS, component, scene graph)
- **`references/performance-guide.md`** — Performance optimization strategies and memory patterns
