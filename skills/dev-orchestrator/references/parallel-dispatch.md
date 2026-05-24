# Parallel Dispatch

Maximize throughput by running non-conflicting agents simultaneously. Every dispatch decision starts with file conflict analysis — never skip it. The orchestrator keeps decision authority; agents perform bounded workstreams and return structured artifacts.

## Iron Law

**Context contamination kills parallel work. Each agent gets a self-contained envelope. No agent reads another agent's output mid-flight — all sharing goes through files and the task system.**

## Per-Task Agent Contract

Agentic implementation uses a fresh bounded agent per task, not a reused broad worker. The orchestrator builds the complete context envelope once, including exact task text, file scope, constraints, verification command, and expected handoff artifact. Agents must not read plan files themselves unless the envelope explicitly grants that scope.

After each implementation task, review runs in order: spec compliance first, code quality second. A quality review cannot start until spec compliance passes or returns a bounded fix task. Any reviewer request for changes creates a narrow follow-up task, then the same review stage repeats before advancing.

Implementer status values are handled explicitly:

| Status | Orchestrator action |
|--------|---------------------|
| `DONE` | Check handoff artifact, then run spec compliance review |
| `DONE_WITH_CONCERNS` | Read concerns; resolve correctness/scope concerns before review, otherwise proceed |
| `NEEDS_CONTEXT` | Add missing context and re-dispatch; do not retry unchanged |
| `BLOCKED` | Change one variable: add context, raise model/agent capability, split task, or escalate to oracle/user |

Never ignore an escalation or force the same prompt to retry unchanged.

## When to Parallelize

Subagent dispatch follows the classification made in `pipeline-operations.md`. Once the pipeline marks work as non-trivial or agentic, split independent research, planning, implementation, verification, and review workstreams before implementation and dispatch the first non-conflicting batch.

| Condition | Decision |
|-----------|----------|
| 2+ subtasks or acceptance checks | Create tasks + dispatch subagents |
| Research/product/design streams are separable | Dispatch separate read-only subagents before plan/impl |
| 3+ likely changed files or 2+ file clusters | Split by file cluster before implementation |
| Tasks write to different file clusters | Parallel — no isolation needed |
| Tasks read same files, write different files | Parallel — reads are safe |
| Tasks write to the same file | Sequential, or worktree isolation |
| failing tests → forge | Sequential — forge blocked by RED evidence |
| forge → prism acceptance/build | Sequential — prism blocked by forge |
| Multiple forge tasks across independent modules | Parallel if file sets are disjoint |
| Build step | Never parallel — always 1 at a time |

## When NOT to Dispatch Subagents

Keep work in the main conversation only when `pipeline-operations.md` classifies it as very lightweight. Otherwise use this reference to choose Agent batches, team mode, sequential execution, or worktree isolation.

## Decision Trace

Before any multi-agent batch, record: decomposition reason, file-conflict map, chosen isolation, blockedBy edges, and why each task is parallel or sequential. Do not rely on agent-to-agent chat; durable state and task records are the coordination surface.

## Harness Coordination Modes

Choose the harness surface that preserves durable coordination without collapsing broad work into a single direct implementation:

| Work shape | Harness mode | Contract |
|------------|--------------|----------|
| 1 bounded task, 1 agent role | `Agent` only | Main conversation owns prompt, scope check, verification, final report |
| 2-3 independent bounded tasks | Multiple `Agent` calls in one message | Use `run_in_background: true`, exact `name`, exact `File Scope`, TaskUpdate after artifact checks |
| Long task with 3+ tasks, staged dependencies, or rolling unblocks | `TeamCreate` + shared `TaskList` + named agents | Team task list is the coordination surface; main conversation is team lead; agents claim/update tasks; lead dispatches newly unblocked work |
| Conflicting writes or risky broad edits | Sequential dispatch, or `Agent` with `isolation: "worktree"` only when supported | Never require git; if git worktrees or WorktreeCreate/WorktreeRemove hooks are unavailable, sequence tasks or use one agent per file cluster without isolation |
| External wait (CI/deploy/remote queue) | `Monitor`/`ScheduleWakeup`, not idle polling agents | Agents do work; harness wait primitive observes terminal state |

Long-running orchestration MUST prefer a team once the task graph has 3+ nodes or requires more than one dispatch wave. Do not simulate teams through chat summaries; use the harness task list, named owners, `blockedBy` edges, and automatic agent completion/idle notifications.

## Dispatch Ritual

Before starting implementation work on standard/deep/autonomous modes, run this explicit dispatch decision:

```
1. INPUT: Read the approved pipeline classification, checked gates, and TaskCreate graph.
2. DIRECT CHECK: If the pipeline classified the task as direct/very lightweight, keep it in the main conversation and still run verification.
3. DECOMPOSE: If one task hides separable research/design/impl/test/review workstreams, create or refine tasks before dispatch.
4. SCAN: Does work span 2+ domains or file clusters? If yes → dispatch subagents.
5. GATES: Does the pipeline need impl + tests + review? → dispatch subagents.
6. DOMAINS: Does work cross frontend/backend, hooks/scripts, skills/tests boundaries? → dispatch subagents.
7. COORDINATION: If task graph has 3+ nodes or multiple waves, create a team before dispatch.
8. CONFLICTS: Build file conflict map (see below).
9. DISPATCH: Send first non-conflicting batch in one message (multiple Agent calls).
```

## File Conflict Analysis

Before dispatching a batch:

```
1. TaskGet each candidate task
2. Extract file paths from "Files:" section and description
3. Build conflict map:
   task_files = {task_id: set(file_paths)}
   conflicts  = {(a, b) for a in tasks for b in tasks if a != b
                         and task_files[a] & task_files[b]}
4. Non-conflicting subset → dispatch in one message (multiple Agent calls)
5. Conflicting pairs → worktree isolation only when supported; otherwise sequence or split into one agent per file cluster
```

If a task description omits exact file paths, ask oracle to refine before dispatching.

## Dispatch Call

All non-conflicting tasks in **one message** (multiple Agent tool calls):

```
Agent({ name: "forge-api", subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope A>" })
Agent({ name: "forge-ui", subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope B>" })
```

Use stable `name` values so `SendMessage` can resume idle teammates. Use `team_name` for team-backed long tasks. Use `isolation: "worktree"` only when file conflict is confirmed and git worktrees or WorktreeCreate/WorktreeRemove hooks are available; otherwise omit isolation and dispatch sequentially.

## Team Mode Ritual

For long tasks, initialize durable coordination before the first dispatch wave:

```
1. TeamCreate({ team_name: "<short-goal>", description: "<goal>", agent_type: "dev-orchestrator" })
2. TaskCreate every planned task with exact File Scope, owner blank, blockedBy edges, verification command, and acceptance criteria
3. Assign ready tasks by TaskUpdate(owner="<agent-name>")
4. Dispatch named agents with matching `team_name`; include their task id and forbid unrelated task claims unless told
5. When an agent reports completion or goes idle, verify its Handoff Artifact, then TaskUpdate(status="completed") or send a bounded correction via SendMessage
6. After each completion, call TaskList; dispatch newly unblocked tasks immediately if file-conflict map allows
7. Shutdown teammates only after final verification/review passes; then TeamDelete if no active members remain
```

Never rely on the idle notification as completion. Idle only means the teammate is waiting for input; completion requires a valid Handoff Artifact plus scope/evidence checks.

## Parallel Limits

| Agent | Max Simultaneous | Notes |
|-------|-----------------|-------|
| forge | 3 | more causes merge chaos |
| prism (unit/integration) | 2 | |
| prism (build) | 1 | build is global state |
| sentinel | 1 per review stage | stage 1 must finish before stage 2 |
| research (general-purpose) | 3 by default | read-only; exceed only with explicit user need |

## Completion Handling

After each agent completes:

1. Verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` matches task scope
3. Verify evidence exists for behavior changes (RED/GREEN)
4. `TaskUpdate(status: "completed")`
5. Scan TaskList for newly unblocked tasks → dispatch next batch immediately
6. Every 3 completed tasks: write summary to `<output_dir>/phase-context.md`

## Decomposition Patterns

### Feature (new behavior)

```
Task 1: Research/product/design streams [general-purpose/oracle] no deps, parallel if independent
Task 2: Types/interfaces                [forge]  blockedBy: [1]
Task 3: Failing unit/acceptance tests    [prism]  blockedBy: [2]
Task 4: Backend implementation          [forge]  blockedBy: [3]
Task 5: Frontend implementation         [forge]  blockedBy: [3]
Task 6: Integration verification        [prism]  blockedBy: [4, 5]
Task 7: Review                          [sentinel] blockedBy: [6]
```

Tasks 4 and 5 run in parallel when both are unblocked and have no file overlap.

### Refactor (restructure without behavior change)

```
Task 1: Impact analysis             [research]  no deps
Task 2: Core structural changes     [forge]  blockedBy: [1], sequential batches
Task 3: Update callers              [forge]  blockedBy: [2], parallel if caller files disjoint
Task 4: Regression tests            [prism]  blockedBy: [all forge]
Task 5: Review                      [sentinel] blockedBy: [4]
```

### Bug Fix (known cause)

Unknown-cause bugs route to `systematic-debugging` before this pattern.

```
Task 1: Write failing test          [prism]  no deps
Task 2: Root cause + fix            [forge]  blockedBy: [1]
Task 3: Verify + run suite          [prism]  blockedBy: [2]
Task 4: Review                      [sentinel] blockedBy: [3] (mandatory for standard/deep/autonomous; optional only in quick)
```

### Large Task (complex, many files)

Split when a task has separable research/design streams, disjoint write clusters, independent domains, separable acceptance criteria, or multiple verification commands.

```
Batch A (parallel): independent research/product/design streams
Batch B (parallel): failing tests or acceptance harnesses by subsystem
Batch C (parallel): implementation tasks with disjoint write sets
Batch D (sequential): tasks whose verification depends on Batch C's output existing
Batch E: integration verification  [prism]  blockedBy: [all impl batches]
Batch F: review                    [sentinel] blockedBy: [E]
```

## Inter-Agent Handoff Protocol

Communication between agents goes through **files and the task system only**.

### forge → prism

Forge's completion must include:
```
STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
FILES_MODIFIED: <exact list>
TEST_COMMAND: <command prism should run>
BUILD_COMMAND: <if applicable>
SELF_REVIEW: <scope drift, missing requirements, risky assumptions, or "PASS">
KNOWN_CONCERNS: <edge cases not covered, or "none">
```

### prism → sentinel

Prism appends to `verification-evidence.jsonl`:
```json
{"phase": "test", "command": "...", "exit_code": 0, "summary": "47 passed, 0 failed"}
```

### forge → forge (discovery sharing)

When forge discovers something other in-flight forge agents need:
1. **STOP** — do not write the shared artifact yourself
2. Create a new blocking task: `TaskCreate({ subject: "Define shared <X>", blockedBy: [] })`
3. Mark your current task `NEEDS_CONTEXT`
4. Orchestrator picks up the new task, dispatches a forge for it, then unblocks the waiting agents

Never have two forge agents write to the same new shared file.

### forge → oracle (escalation)

When forge is blocked on a design decision not in the plan:
1. Task status → `BLOCKED`
2. Write question to `<output_dir>/phase-context.md` (tag: `[ESCALATION]`)
3. Orchestrator routes to oracle for a decision
4. Oracle appends decision (tag: `[DECISION]`)
5. Orchestrator re-dispatches forge with decision injected

## Red Flags

- Dispatching an agent without a self-contained envelope
- Dispatching agents for tasks with file conflicts without isolation
- Letting a forge agent "figure out" the file scope
- Running prism build in parallel with any forge write
- An agent that writes to a file it didn't declare in `File Scope`

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "Fix all the tests" — too broad | One agent per test file or subsystem |
| No context in dispatch | Paste error messages and test names |
| No constraints on agent | "Do NOT change production code" or "Fix tests only" |
| Vague output request | "Return summary of root cause and changes" |
| Skipping file conflict analysis | Always build conflict map before dispatch |

## Fresh-Agent Task Envelope

Every implementation dispatch uses a fresh bounded agent per task. The envelope must include task text, exact file scope, relevant specs, constraints, verification command, allowed write set, and required handoff fields. Do not ask the agent to infer scope from plan files unless those files are explicitly part of the read scope.

Use one agent per independent problem domain when failures or workstreams are separable. Keep related failures together when one fix may resolve several failures.

If an agent returns NEEDS_CONTEXT, add the missing context and re-dispatch. If an agent returns BLOCKED, change one variable before retry: split the task, improve the envelope, raise capability, sequence conflicting work, or escalate. The same prompt must not be retried unchanged.

## Envelope Completeness Checklist

Each agent envelope must include the allowed write set, exact read scope, task id, acceptance criterion, verification command, and file-conflict map. If the file-conflict map is missing, stop and refine tasks before dispatch.

Team mode requires named owners for ready work, explicit blockedBy edges, and immediate scheduling of newly unblocked tasks after each valid handoff. Idle is not completion; only a checked handoff artifact plus evidence can complete a task.

## Conflict Recovery Matrix

| Conflict | Action |
|---|---|
| same file writes | sequence the tasks or isolate with a supported worktree |
| shared new artifact | create a blocking task for the artifact before dependent work continues |
| broad unknown write set | stop dispatch and refine file scope |
| verification uses global state | run one prism/build lane at a time |

Never resolve conflicts by letting agents coordinate ad hoc. The orchestrator owns conflict recovery.
