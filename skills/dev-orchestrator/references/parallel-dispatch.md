# Parallel Dispatch

Maximize throughput by running non-conflicting agents simultaneously. Every dispatch decision starts with file conflict analysis — never skip it. The orchestrator keeps decision authority; agents perform bounded workstreams and return structured artifacts.

## Iron Law

**Context contamination kills parallel work. Each agent gets a self-contained envelope. No agent reads another agent's output mid-flight — all sharing goes through files and the task system.**

## When to Parallelize

Subagent dispatch is the default for non-trivial work, not an optimization to remember later. Research and planning are also default-on for non-trivial work; skip them only for trivial tasks. Keep implementation in the main conversation only for trivial tasks. If a task can be split into independent research, planning, implementation, or verification workstreams, split it before implementation and dispatch the first non-conflicting batch.

| Condition | Decision |
|-----------|----------|
| 3+ subtasks or acceptance checks | Create tasks + dispatch subagents |
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

Keep work in the main conversation only when all are true: narrow scope, likely one file, obvious implementation, no behavior/design ambiguity, single verification command, and no review/acceptance handoff needed. Do not create agents just to edit one clear line or run one command.

## Decision Trace

Before any multi-agent batch, record: decomposition reason, file-conflict map, chosen isolation, blockedBy edges, and why each task is parallel or sequential. Do not rely on agent-to-agent chat; durable state and task records are the coordination surface.

## Dispatch Ritual

Before starting implementation work on standard/deep/autonomous modes, run this explicit dispatch decision:

```
1. TRIVIAL: Is this narrow, obvious, likely one file, unambiguous, one verification command, and no independent review/acceptance handoff? If yes → main conversation may implement directly.
2. DECOMPOSE: Is this one broad request hiding separable research/design/impl/test/review workstreams? If yes → create tasks first.
3. COUNT: How many subtasks/acceptance checks after decomposition? If ≥2 → dispatch subagents.
4. SCAN: How many files likely changed? If ≥2 or spanning 2+ clusters → dispatch subagents.
5. GATES: Does the pipeline need impl + tests + review? → dispatch subagents.
6. DOMAINS: Does work cross frontend/backend, hooks/scripts, skills/tests boundaries? → dispatch subagents.

If TRIVIAL is yes and every other check is no:
  - Do work directly in main conversation
  - Still run verification gate after completion

Otherwise:
  - Create TaskCreate tasks with blockedBy
  - Include separate research/product/design tasks when they can run independently
  - Build file conflict map (see below)
  - Dispatch first non-conflicting batch in one message (multiple Agent calls)
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
5. Conflicting pairs → worktree isolation OR sequence
```

If a task description omits exact file paths, ask oracle to refine before dispatching.

## Dispatch Call

All non-conflicting tasks in **one message** (multiple Agent tool calls):

```
Agent({ subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope A>" })
Agent({ subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope B>" })
```

Use `isolation: "worktree"` only when file conflict is confirmed.

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
- Files modified: <exact list>
- Test command: <command prism should run>
- Build command: <if applicable>
- Known concerns: <edge cases not covered, or "none">
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
