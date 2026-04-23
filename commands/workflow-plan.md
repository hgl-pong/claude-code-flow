---
name: workflow-plan
description: Start the planning pipeline — oracle analyzes the task, produces a phased implementation plan (HTML for complex features), and waits for approval before proceeding to implementation.
---

# Workflow Plan

Start the planning pipeline for a feature or task.

## Process

1. **Analyze** the user's request to classify:
   - **Domain**: What area of the codebase is affected
   - **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
   - **Needs design**: Yes (new system/architectural change) vs No (feature addition/bug fix)
   - **Needs research**: Yes (external library/API, best practices lookup, tech comparison) vs No (internal-only)

2. **Research** (if needed): invoke scout to gather external information:
   - Documentation, API references, library usage patterns
   - Technology comparisons and best practices
   - Version compatibility and deprecation warnings
   - Feed research findings into oracle's planning context

3. **Invoke oracle** to create a plan:
   - **Complex**: oracle generates HTML visualization with architecture, phases, dependencies, risks
   - **Simple**: oracle produces a text summary with files to change, risks, and approach

4. **Wait for user approval** — do NOT proceed until the user confirms the plan

5. **If needs design**: invoke atlas (Opus) for architecture design, wait for approval

6. **Hand off to implementation**: spawn forge (and prism/anvil as needed) with the approved plan

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan Refactor the database layer to use repository pattern
/workflow-plan Fix the memory leak in the connection pool
```

## After Plan Approval

Distribute work to agents based on task type:
- Implementation → forge
- Tests → prism
- Build/CI → anvil
- For complex tasks with 4+ subtasks, use Team + TaskList for parallel execution
