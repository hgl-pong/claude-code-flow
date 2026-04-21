---
name: Game Engine Dev
description: This skill should be used when the user asks to "develop a game engine feature", "implement an engine system", "design engine architecture", "add a renderer", "build a physics system", "create an ECS", "set up the build system", "write engine tests", or mentions game engine development tasks involving C++, Lua, HLSL, or CMake. Triggers on any multi-step game engine development task that benefits from agent orchestration and model-tiered delegation.
---

# Game Engine Development Orchestrator

Orchestrate game engine development tasks through a structured pipeline with model-tiered agents. Every task passes through **Plan → Implement → Review** gates, with HTML visualization for complex plans.

## Agent Roster

| Agent | Model | Role | Tools | Gate |
|-------|-------|------|-------|------|
| `game-engine-dev:plan-agent` | opus | Implementation planning, phased roadmap, HTML visualization | Read,Grep,Glob,Write,Bash | Plan Gate |
| `game-engine-dev:architect` | opus | Architecture design, module decomposition, ECS design | Read,Grep,Glob | Design Gate |
| `game-engine-dev:core-developer` | sonnet | C++/Lua/HLSL implementation | Read,Write,Edit,Grep,Glob,Bash | Implementation |
| `game-engine-dev:test-engineer` | sonnet | Test frameworks, unit/integration/performance tests | Read,Write,Edit,Grep,Glob,Bash | Verification |
| `game-engine-dev:build-engineer` | haiku | CMake, CI/CD, cross-platform compilation | Read,Write,Edit,Grep,Glob,Bash | Build Gate |
| `game-engine-dev:review-agent` | sonnet | Code review, correctness/performance/architecture check | Read,Grep,Glob | Review Gate |

## Universal Pipeline

Every task, regardless of complexity, follows this pipeline. The difference is how many stages are active.

```
┌─────────────────────────────────────────────────────────┐
│                    PLAN GATE                            │
│  plan-agent (Opus)                                       │
│  Complex: HTML visualization → user browser review      │
│  Simple: text summary → user inline approval            │
│  ⛔ Blocked until user approves the plan                │
└──────────────────────┬──────────────────────────────────┘
                       │ approved
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 DESIGN GATE (if needed)                  │
│  architect (Opus) — detailed system design              │
│  ⛔ Blocked until design is complete                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 IMPLEMENTATION                           │
│  core-developer (Sonnet) + test-engineer (Sonnet)       │
│  + build-engineer (Haiku) — parallel where possible     │
└──────────────────────┬──────────────────────────────────┘
                       │ implementation done
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  REVIEW GATE                             │
│  review-agent (Sonnet) — checks all changed files       │
│  ✅ Pass → proceed to report                            │
│  ❌ Fail → back to core-developer for fixes → re-review │
│  ⛔ Blocked until review passes                         │
└──────────────────────┬──────────────────────────────────┘
                       │ review passed
                       ▼
                   Report & Done
```

## Step 1: Analyze the Task

Read the user's request and classify:
- **Domain**: Rendering, Physics, Audio, ECS, Input, Resource Management, Build System, Testing
- **Complexity**: Simple (1-2 subtasks, single domain) vs Complex (3+ subtasks, cross-cutting)
- **Needs design**: Yes (new system, architectural change) vs No (bug fix, feature addition to existing system)

## Step 2: Plan Gate

**Always** invoke plan-agent, regardless of complexity. The difference is output format:

**Complex tasks** (new system, multi-module, architectural):
- plan-agent generates self-contained HTML visualization
- Include: architecture diagram, phase timeline, dependency graph, risk table, file impact tree
- Save HTML to temp file, open in browser for user review
- Wait for user feedback; iterate until approved

**Simple tasks** (bug fix, single feature, config change):
- plan-agent produces a brief text summary: what to change, which files, risks
- Present inline to user for quick approval
- No HTML needed

**Plan-agent prompt template:**
```
Task: [user's request]
Complexity: [simple|complex]
Codebase context: [existing architecture notes]
Output: [HTML file path | text summary]
```

⛔ Do NOT proceed to implementation until the user approves the plan.

## Step 3: Design Gate (if needed)

Skip for: bug fixes, small features on existing systems, build/CI tasks.

For new systems or architectural changes:
1. Spawn **architect** (Opus) with the approved plan as context
2. Architect produces: module design, API surface, data layout, file structure
3. Present the design to the user for confirmation (can be inline, no HTML needed)
4. Wait for approval before implementation

## Step 4: Implementation

Decompose the approved plan+design into concrete subtasks. Use orchestration mode based on task count:

**Simple mode** (1-3 subtasks):
```
Agent({ name: "dev", subagent_type: "game-engine-dev:core-developer", model: "sonnet", prompt: "..." })
```

**Complex mode** (4+ subtasks, parallel work):
```
TeamCreate({ team_name: "engine-feature-x" })
TaskCreate({ subject: "...", addBlockedBy: [...] })  // set dependencies
Agent({ name: "dev-1", team_name: "...", subagent_type: "game-engine-dev:core-developer", model: "sonnet", prompt: "..." })
Agent({ name: "test-1", team_name: "...", subagent_type: "game-engine-dev:test-engineer", model: "sonnet", prompt: "..." })
```

**Parallel execution rules:**
- core-developer and test-engineer can work in parallel if tests are for existing (not new) code
- build-engineer can work in parallel with test-engineer
- architect and core-developer are always sequential (design before code)

## Step 5: Review Gate

After implementation completes, **always** invoke review-agent:

```
Agent({
  name: "reviewer",
  subagent_type: "game-engine-dev:review-agent",
  model: "sonnet",
  prompt: """
  Review the following changes for the task: [task description]
  Plan reference: [path to approved plan, if exists]
  Files created: [list of new files]
  Files modified: [list of changed files]
  Focus areas: [any specific concerns]
  """
})
```

**Review outcome handling:**
- **APPROVE** → proceed to report
- **REQUEST CHANGES** → collect the issue list, delegate fixes back to core-developer, then re-run review-agent
- **NEEDS DISCUSSION** → present findings to user, ask for direction

The review loop continues until review-agent returns APPROVE. Maximum 3 iterations; if still failing after 3, escalate to user.

## Complete Workflow Examples

### Example 1: Complex New System

```
User: "Build a physics system with rigid body and collision detection"

1. PLAN GATE: plan-agent (Opus)
   → HTML with: 4 phases, architecture diagram, 12 files to create, 3 risks
   → User reviews in browser, approves with feedback: "skip fluid simulation for now"
   → plan-agent revises plan

2. DESIGN GATE: architect (Opus)
   → Module design: physics/, collision/, broadphase/, narrowphase/
   → API surface: PhysicsWorld, RigidBody, Collider, CollisionEvent
   → User approves

3. IMPLEMENTATION: core-developer (Sonnet) + test-engineer (Sonnet) + build-engineer (Haiku)
   → Parallel: core-developer implements, test-engineer writes tests, build-engineer updates CMake

4. REVIEW GATE: review-agent (Sonnet)
   → Reviews 12 new files
   → Finds: missing alignment in RigidBody struct (critical), TODO in collision resolver (warning)
   → Back to core-developer for fixes → re-review → APPROVE

5. REPORT: Summary with file list and review status
```

### Example 2: Simple Bug Fix

```
User: "Fix the memory leak in ResourceLoader::load"

1. PLAN GATE: plan-agent (Opus)
   → Text summary: "Investigate ResourceLoader::load, fix leak, add regression test. Files: resource_loader.cpp, test_resource.cpp"
   → User approves inline

2. DESIGN GATE: skipped (bug fix)

3. IMPLEMENTATION: core-developer (Sonnet)
   → Fixes the leak, test-engineer adds regression test

4. REVIEW GATE: review-agent (Sonnet)
   → Reviews 2 files → APPROVE

5. REPORT: Done
```

### Example 3: Build Configuration

```
User: "Add vcpkg integration and add SDL2 + ImGui"

1. PLAN GATE: plan-agent (Opus)
   → Text summary: "Add vcpkg.json, update CMakeLists.txt, add find_package calls"
   → User approves

2. DESIGN GATE: skipped
3. IMPLEMENTATION: build-engineer (Haiku)

4. REVIEW GATE: review-agent (Sonnet)
   → Reviews CMakeLists.txt and vcpkg.json → APPROVE

5. REPORT: Done
```

## Task Prompting Guidelines

For all agents, include in the prompt:
- **Context**: Overall project goal and where this task fits
- **Scope**: Exactly what this agent should produce
- **Constraints**: Files to modify, patterns to follow, APIs to use
- **Dependencies**: What other agents are producing (if known)
- **Output**: What the agent should return

For **plan-agent**: also specify complexity level and whether HTML is needed.
For **review-agent**: also specify files to review, plan reference path, and focus areas.

## Additional Resources

- **`references/architecture-patterns.md`** — ECS, frame graph, memory allocator patterns
- **`references/performance-guide.md`** — SIMD, profiling, concurrency patterns
