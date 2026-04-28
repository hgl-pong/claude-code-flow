---
name: workflow-plan
description: Start the planning pipeline — oracle analyzes the task, produces a phased implementation plan (HTML for complex features), and waits for approval before proceeding to implementation.
---

# Workflow Plan

Start the planning pipeline for a feature or task.

## Arguments

```
/workflow-plan [--mode quick|standard|deep|autonomous] <task description>
/workflow-plan <task description>
```

- `--mode`: Override automatic mode selection. If omitted, the orchestrator auto-recommends based on task analysis.
- `task description`: What to build, fix, or implement.

## Process

1. **Parse arguments**: Extract mode override (if any) and task description

2. **Analyze** the user's request to classify:
   - **Domain**: `frontend-ui` (pages, components, styles, layouts) or `backend/general`
   - **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
   - **Needs design**: Yes (new system/architectural change) vs No (feature addition/bug fix)
   - **Needs UI design**: Yes if domain is `frontend-ui` and not a trivial CSS tweak
   - **Needs research**: Yes (external library/API, best practices lookup, tech comparison) vs No (internal-only)

3. **Select mode** (if not overridden by user):
   - 1-2 subtasks, single domain → **quick**
   - 3-5 subtasks, known codebase → **standard**
   - 6+ subtasks, new system, cross-module → **deep**
   - User says "figure it out" → **autonomous**
   - Present recommendation and ask for confirmation

4. **Set mode and state**:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
   python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
   ```

5. **Research** (if needed and not quick mode): invoke scout to gather external information

6. **Invoke oracle** to create a plan based on mode:
   - **quick**: Minimal inline plan or skip directly to implementation
   - **standard**: Text summary with files to change, risks, and approach
   - **deep**: HTML visualization with architecture, phases, dependencies, risks
   - **autonomous**: Full plan with auto-approval

7. **Wait for user approval** — skip in autonomous mode

8. **If needs design** (deep/autonomous + new system): invoke atlas (Opus) for architecture design, wait for approval

9. **If needs UI design** (frontend-ui, standard+): invoke scout for UI research → invoke designer for design document → wait for approval

10. **Hand off to implementation**:
    - Frontend-UI → weaver (with design doc from step 9)
    - Backend/General → forge
    - Tests → prism, Build/CI → anvil (as needed)

## Usage

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan --mode deep Refactor the database layer to use repository pattern
/workflow-plan --mode quick Fix the memory leak in the connection pool
/workflow-plan --mode autonomous Build a REST API for the user management module
```

## After Plan Approval

### Domain Routing

Distribute work to agents based on task domain and mode:

**Frontend-UI tasks** (new pages, UI components, layout changes, visual features):
1. **UI Research** (standard+): invoke scout to research similar product patterns, design trends → save to `ui-research.md`
2. **UI Design Gate** (standard+): invoke designer to produce design document → user approval
3. **Implementation** → weaver (with design doc as context)
4. **Tests** → prism
5. **Build/CI** → anvil

**Backend/General tasks**:
1. **Implementation** → forge
2. **Tests** → prism
3. **Build/CI** → anvil

### Scheduling

- For standard/deep/autonomous, use TaskCreate/TaskList for task tracking with blockedBy dependencies
- Group tasks by agent type, dispatch multiple Agent calls in a single message (max 2 concurrent)
- Check for shared file conflicts before parallel dispatch — serialize overlapping tasks
- Weaver tasks blocked by designer completion (set via blockedBy)
- On agent completion: TaskUpdate status=completed, then check TaskList for newly unblocked tasks
