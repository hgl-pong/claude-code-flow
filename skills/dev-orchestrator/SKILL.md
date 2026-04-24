---
name: Dev Orchestrator
version: "2.0.0"
description: This skill should be used when the user asks to "develop a feature", "implement a system", "design architecture", "build an API", "refactor a module", or any multi-step development task that benefits from agent orchestration and model-tiered delegation. Triggers on complex development tasks where planning, implementation, testing, and review should be coordinated.
---

# Development Orchestrator

Orchestrate tasks through Plan -> Implement -> Review pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and dynamic error recovery.

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

## Mode Selection — Smallest Mode That Fits

After analysis, select the appropriate workflow mode:

| Mode | When | Research | Design | Plan Approval | Review | Auto-retry |
|------|------|----------|--------|---------------|--------|------------|
| **quick** | Bug fix, single file, config change | No | No | No | Optional | No |
| **standard** | Feature addition, multi-file change | If needed | No | Yes | Yes | No |
| **deep** | New system, architecture refactor, complex integration | Yes | Yes | Yes (HTML) | Yes | Yes |
| **autonomous** | User gives goal, expects full delivery | Auto | Auto | Auto | Auto (max 3) | Yes |

Set mode via:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
```

Auto-recommend logic:
- 1-2 subtasks, single domain, no external deps → **quick**
- 3-5 subtasks, known codebase → **standard**
- 6+ subtasks, new system, cross-module → **deep**
- User says "figure it out" / "just ship it" → **autonomous**

User can override the recommendation. If user specified `--mode` in `/workflow-plan`, use that mode.

## Pipeline

```
Mode Selection
      |
      v
Research (scout) -- if needed (skipped in quick mode)
      |
      v
Plan Gate (oracle)
  quick:   skip or minimal inline plan
  standard: text summary -> inline approval
  deep:    HTML viz -> browser review
  auto:    auto-approve
      |
      v
Design Gate (atlas) -- only for deep mode / new systems
      |
      v
Implementation (forge + prism + anvil)
  DAG-aware scheduling for deep/standard
  Direct call for quick
      |
      v
Review Gate (sentinel)
  quick:   optional
  standard/deep: mandatory
  auto:    auto-handle feedback (max 3 rounds)
      |
      v
Documentation (chronicler) -- if needed
      |
      v
Report & Done
```

## State Machine

Write state at each transition:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>
```

Valid transitions:
```
idle -> research     (external info needed)
idle -> plan         (no research needed)
research -> plan     (research complete)
plan -> design       (plan approved, needs architecture)
plan -> impl         (plan approved, no architecture needed)
design -> impl       (design approved)
impl -> review       (implementation complete)
review -> impl       (review failed, back to forge)
review -> idle       (review passed)
impl -> idle         (simple/quick task, skip review)
* -> idle            (user cancels or error)
```

## Context Preservation

| File | Written by | Read by | Content |
|------|-----------|---------|---------|
| `.claude/flow/workflow-state.json` | flow-state.py | statusline, orchestrator | Phase, mode, task progress, retry count |
| `.claude/flow/phase-context.md` | oracle/atlas | forge/sentinel | Approved plan, architecture decisions |
| `.claude/flow/modified-files.txt` | track-changes.py | sentinel | Files modified (plain list) |
| `.claude/flow/modified-files.jsonl` | track-changes.py | orchestrator | File ownership log (file, action, agent, ts) |
| `.claude/flow/review-result.txt` | sentinel | orchestrator | Latest review outcome |
| `.claude/flow/task-graph.json` | oracle | orchestrator | DAG task structure |

**Phase handoff protocol:**
1. After plan approval: oracle writes plan summary to `phase-context.md` with YAML frontmatter (written_by, phase, timestamp, session_id, task_summary)
2. After design approval: atlas appends architecture decisions to `phase-context.md`
3. Before review: orchestrator lists modified files for sentinel
4. After review: sentinel writes outcome to `review-result.txt`

## Step 1: Analyze + Mode Select

Classify the task:
- **Domain**: What area of the codebase is affected
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
- **Needs design**: Yes (new system) vs No (bug fix, feature addition)
- **Needs research**: Yes (external library/API) vs No (internal-only)

Select mode based on the classification (see Mode Selection table above).
Set mode and initial phase:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 2: Research (if needed)

Skip for: quick mode, internal-only tasks, or when user already has context.

Invoke scout when external information is needed (library docs, API references, tech comparisons).

```
Agent({
  name: "researcher",
  subagent_type: "claude-code-flow:scout",
  model: "sonnet",
  prompt: """
  Research topic: [specific question or area]
  Context: [task description]
  What we need: [specific information gaps]
  """
})
```

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 3: Plan Gate

**quick mode**: Skip to implementation. At most, write a 2-line plan inline.

**standard mode**: Invoke oracle for text summary (files to change, risks, approach).

**deep mode**: Invoke oracle for HTML visualization (architecture, phases, dependencies, risk table).

**autonomous mode**: Invoke oracle. Auto-approve the plan.

After approval, oracle writes plan summary to `.claude/flow/phase-context.md` with frontmatter.

For standard/deep/autonomous modes, oracle also generates `.claude/flow/task-graph.json` (see Step 5: DAG Scheduling).

## Step 4: Design Gate (if needed)

Skip for: quick/standard mode, bug fixes, small features.

For new systems or architectural changes (deep/autonomous mode):
1. Spawn **atlas** (Opus) with approved plan as context
2. atlas produces: module design, API surface, data layout, file structure
3. Present to user for confirmation (auto-approve in autonomous mode)
4. After approval, atlas appends to `phase-context.md`

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase design
```

## Step 5: Implementation (DAG-Aware Scheduling)

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
```

### DAG Task Graph

For standard/deep/autonomous modes, tasks are structured as a DAG in `.claude/flow/task-graph.json`:
```json
{
  "nodes": [
    {"id": "T1", "title": "...", "agent": "forge", "status": "pending", "dependencies": [], "files": [...]},
    {"id": "T2", "title": "...", "agent": "forge", "status": "pending", "dependencies": ["T1"], "files": [...]}
  ],
  "edges": [["T1","T2"]]
}
```

### Scheduling Loop

```
while get-ready tasks exist:
  1. Run: python hooks/scripts/task-graph.py get-ready
  2. Group ready tasks by agent type
  3. Spawn agents in parallel for independent tasks (max 2 parallel agents)
  4. On completion: set-status <id> done, update task progress
  5. Check for failed tasks -> dynamic re-planning (Step 7)
  6. Loop back to 1
```

**Parallel rules:**
- forge + prism can parallel if tests are for existing code
- anvil can parallel with prism
- Tasks with shared file dependencies must NOT run in parallel
- Use `modified-files.jsonl` ownership data to detect potential conflicts

**quick mode**: Skip DAG. Direct single forge call.

Update task progress:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-tasks <done> <total>
```

### Context Management

- After every 3 completed tasks, generate an intermediate state summary
- Write key decisions to `phase-context.md` incrementally
- If remaining tasks > 5, suggest the user allow context compaction
- On compaction, `on-compact.py` preserves current state to `pre-compact-context.md`

## Step 6: Review Gate

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase review
```

**quick mode**: Review is optional. Ask user if they want it.

**standard/deep mode**: Always invoke sentinel.

**autonomous mode**: Auto-invoke sentinel and auto-handle feedback.

```
Agent({
  name: "reviewer",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
  Task: [task description]
  Plan reference: .claude/flow/phase-context.md
  Files created: [list from modified-files.jsonl]
  Focus areas: [specific concerns]
  """
})
```

Outcomes:
- APPROVE -> write to `review-result.txt`, proceed
- REQUEST CHANGES -> back to forge with specific feedback -> re-review
- NEEDS DISCUSSION -> present to user

Max 3 review rounds. Escalate to user after that.

### Rule Check

If `.claude/flow/rules.json` exists, sentinel also checks modified files against accumulated rules. Any violations are flagged as "RULE VIOLATION" in the review report.

## Step 7: Dynamic Re-Planning (Error Recovery)

When a task fails, use the four-level decision framework:

```
Failure detected
  -> Classify error: syntax / dependency / logic / environment / unknown
  |
  +-- syntax error     -> FIX: auto-correct and retry
  +-- dependency error -> FIX: install missing dependency and retry
  +-- logic error      -> INVESTIGATE: analyze context, then FIX or ESCALATE
  +-- environment error -> ESCALATE: needs user intervention
  +-- unrelated issue   -> NOTE: record as known issue, skip and continue
  +-- unknown           -> INVESTIGATE -> max 2 FIX attempts -> ESCALATE
```

Implementation:
1. On agent failure, log error: `python hooks/scripts/flow-state.py set-error <task_id> <type> <message>`
2. Increment retry: `python hooks/scripts/flow-state.py inc-retry`
3. Based on error classification:
   - **FIX**: Re-invoke agent with error context. Prompt: "Previous attempt failed with: [error]. Fix the issue and retry."
   - **INVESTIGATE**: Read relevant files, check error logs, analyze context. Then decide FIX or ESCALATE.
   - **NOTE**: Write to `phase-context.md` as a known caveat. Mark task as done with a note. Continue with remaining tasks.
   - **ESCALATE**: Pause workflow. Present to user with options: retry manually, skip step, or cancel.
4. Record the decision and resolution to `.claude/flow/error-log.jsonl`

Max retries per task: 2. After that, always ESCALATE.

## Step 8: Documentation (optional)

After implementation passes review, invoke chronicler if:
- The feature adds new public APIs
- The user requested documentation
- The project has a docs/ directory with existing documentation

## Step 9: Report & Done

Write final state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase idle
```

Present final summary:
- What was implemented
- Files created/modified (from modified-files.jsonl ownership data)
- Test results
- Review outcome
- Any known issues noted during execution

## Prompting Guidelines

For all agents, include: Context, Scope, Constraints, Dependencies, Output.

For **scout**: research topic, info gaps, how findings feed into planning.
For **oracle**: complexity level, mode, HTML requirement, research findings.
For **forge**: specific files, plan reference, task from DAG, related files to avoid breaking.
For **sentinel**: files to review, plan path, focus areas, rules to check.
For **chronicler**: doc style, target audience.
