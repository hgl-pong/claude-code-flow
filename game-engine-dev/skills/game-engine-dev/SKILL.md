---
name: Game Engine Dev
description: This skill should be used when the user asks to "develop a game engine feature", "implement an engine system", "design engine architecture", "add a renderer", "build a physics system", "create an ECS", "set up the build system", "write engine tests", or mentions game engine development tasks involving C++, Lua, HLSL, or CMake. Triggers on any multi-step game engine development task that benefits from agent orchestration and model-tiered delegation.
---

# Game Engine Development Orchestrator

Orchestrate game engine development tasks by analyzing complexity, decomposing work, and delegating to specialized agents with appropriate model tiers.

## Agent Roster

| Agent | Model | Role | Color |
|-------|-------|------|-------|
| `game-engine-dev:architect` | opus | Architecture design, module decomposition, ECS design, performance strategy | magenta |
| `game-engine-dev:core-developer` | sonnet | C++/Lua/HLSL implementation, memory management, concurrency | blue |
| `game-engine-dev:test-engineer` | sonnet | Test frameworks, unit/integration/performance tests | green |
| `game-engine-dev:build-engineer` | haiku | CMake, CI/CD, cross-platform compilation, dependency management | yellow |

## Orchestration Workflow

### Step 1: Analyze the Task

Read the user's request and classify it by:
- **Domain**: Rendering, Physics, Audio, ECS, Input, Resource Management, Build System, Testing
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting concerns)
- **Phase**: Design, Implementation, Testing, Build/Deploy

### Step 2: Decompose into Subtasks

Break the task into concrete, assignable subtasks. Each subtask should:
- Have a clear deliverable (file, module, test, config)
- Map to exactly one agent
- Be independently verifiable

**Decomposition patterns by domain:**

- **New system/feature** → Architect designs first, then core-developer implements, test-engineer writes tests
- **Bug fix** → Core-developer investigates and fixes, test-engineer adds regression test
- **Build/CI issue** → Build-engineer handles directly
- **Performance optimization** → Architect analyzes and proposes, core-developer implements, test-engineer benchmarks
- **Architecture refactor** → Architect plans, core-developer executes, test-engineer validates, build-engineer updates build

### Step 3: Choose Orchestration Mode

**Simple mode** (1-2 subtasks, single domain):
- Use the `Agent` tool directly to spawn agents with explicit `model` parameter
- Sequential execution, results flow back to the conversation

**Complex mode** (3+ subtasks, cross-cutting):
- Use `TeamCreate` to create a team
- Use `TaskCreate` to create tasks with dependencies (`addBlockedBy`)
- Use `Agent` tool with `team_name` to spawn teammates
- Agents self-coordinate via TaskList

### Step 4: Execute with Model Assignment

When spawning agents, always specify the `model` parameter:

```
Agent({
  name: "architect",
  team_name: "...",        // if complex mode
  subagent_type: "game-engine-dev:architect",
  model: "opus",
  prompt: "..."
})
```

**Model selection rules:**
- `opus` — Only for architect: complex reasoning, system design, trade-off analysis
- `sonnet` — For core-developer and test-engineer: code generation, test writing, implementation
- `haiku` — For build-engineer: config files, build scripts, CI pipelines (fast, low-cost)

### Step 5: Aggregate and Validate

After all agents complete:
1. Collect results from each agent
2. Verify cross-agent consistency (architect's design matches implementation)
3. Check that build-engineer's config covers all new files
4. Confirm test-engineer's tests cover core-developer's changes
5. Report summary to user with file-level change list

## Task Prompting Guidelines

When delegating to agents, include in the prompt:
- **Context**: What the overall project goal is
- **Scope**: Exactly what this agent should produce
- **Constraints**: Files to modify, patterns to follow, APIs to use
- **Dependencies**: What other agents are producing (if known)
- **Output**: What the agent should return

## Additional Resources

- **`references/architecture-patterns.md`** — Common game engine architecture patterns (ECS, component, scene graph)
- **`references/performance-guide.md`** — Performance optimization strategies and memory patterns
