---
name: Dispatching Parallel Agents
version: "1.0.0"
description: "Use for: splitting large tasks across multiple agents, parallel execution, file-conflict analysis, agent handoff. Triggers when dev-orchestrator has 3+ independent subtasks."
---

# Dispatching Parallel Agents

Maximize throughput by running non-conflicting agents simultaneously. Every dispatch decision starts with file conflict analysis — never skip it.

## Iron Law

**Context contamination kills parallel work. Each agent gets a self-contained envelope. No agent reads another agent's output mid-flight — all sharing goes through files and the task system.**

## When to Parallelize

| Condition | Decision |
|-----------|----------|
| Tasks write to different file clusters | Parallel — no isolation needed |
| Tasks read same files, write different files | Parallel — reads are safe |
| Tasks write to the same file | Sequential, or worktree isolation |
| forge → prism (tests need implementation) | Sequential — prism blocked by forge |
| Multiple forge tasks across independent modules | Parallel if file sets are disjoint |
| Build step | Never parallel — always 1 at a time |

## Task Decomposition Patterns

Oracle uses these patterns when writing plans for large tasks.

### Feature (new behavior)

```
Task 1: Types/interfaces            [forge]  no deps
Task 2: Backend implementation      [forge]  blockedBy: [1]
Task 3: Frontend implementation     [forge]  blockedBy: [1]
Task 4: Tests — unit                [prism]  blockedBy: [2, 3]
Task 5: Tests — integration         [prism]  blockedBy: [4]
Task 6: Review                      [sentinel] blockedBy: [5]
```

Tasks 2 and 3 run in parallel (both blocked by 1, no file overlap).

### Refactor (restructure without behavior change)

```
Task 1: Impact analysis             [scout]  no deps
Task 2: Core structural changes     [forge]  blockedBy: [1], sequential batches
Task 3: Update callers              [forge]  blockedBy: [2], parallel if caller files disjoint
Task 4: Regression tests            [prism]  blockedBy: [all forge]
Task 5: Review                      [sentinel] blockedBy: [4]
```

### Bug Fix (unknown cause)

```
Task 1: Write failing test          [prism]  no deps
Task 2: Root cause + fix            [forge]  blockedBy: [1]
Task 3: Verify + run suite          [prism]  blockedBy: [2]
Task 4: Review (optional)           [sentinel] blockedBy: [3]
```

### Large Task (complex, many files)

Split when a task needs **multiple independent verification commands** — each verifiable piece becomes its own task. A rename touching 20 files has one verification command (`grep` + test suite), so it stays one task.

```
Batch A (parallel): tasks with disjoint write sets, each independently verifiable
Batch B (sequential): tasks whose verification depends on Batch A's output existing
Batch C (parallel with B if no write conflicts): additional independent verifiable units
Batch D: integration verification  [prism]  blockedBy: [all impl batches]
Batch E: review                    [sentinel] blockedBy: [D]
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

If a task description omits exact file paths, ask oracle to refine the task before dispatching.

## Dispatch Call

All non-conflicting tasks in **one message** (multiple Agent tool calls):

```
Agent({ subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope A>" })
Agent({ subagent_type: "claude-code-flow:forge", run_in_background: true, prompt: "<envelope B>" })
Agent({ subagent_type: "claude-code-flow:prism", run_in_background: true, prompt: "<envelope C>" })
```

Use `isolation: "worktree"` only when file conflict is confirmed.

## Parallel Limits

| Agent | Max Simultaneous | Notes |
|-------|-----------------|-------|
| forge | 3 | more causes merge chaos |
| prism (unit/integration) | 2 | |
| prism (build) | 1 | build is global state |
| sentinel | 1 per review stage | stage 1 must finish before stage 2 |
| scout | unlimited | read-only, no conflicts |

## Inter-Agent Handoff Protocol

Communication between agents goes through **files and the task system only** — not through shared in-flight context.

### forge → prism

Forge's `Completion Schema` must include:
```
- Files modified: <exact list>
- Test command: <command prism should run>
- Build command: <if applicable>
- Known concerns: <edge cases not covered, or "none">
```

Prism reads this from the completed task's output. Never assume prism can infer the test command.

### prism → sentinel

Prism appends to `verification-evidence.jsonl`:
```json
{"phase": "test", "command": "...", "exit_code": 0, "summary": "47 passed, 0 failed"}
```
Sentinel's envelope includes the path to this file. Sentinel reads evidence before reviewing code.

### forge → forge (discovery sharing)

When forge discovers something other in-flight forge agents need (shared type, utility function, API contract change):
1. **STOP** — do not write the shared artifact yourself
2. Create a new blocking task: `TaskCreate({ subject: "Define shared <X>", blockedBy: [] })`
3. Mark your current task `NEEDS_CONTEXT`
4. Orchestrator picks up the new task, dispatches a forge for it, then unblocks the waiting agents

Never have two forge agents write to the same new shared file — one owns it.

### forge → oracle (escalation)

When forge is blocked on a design decision not in the plan:
1. Task status → `BLOCKED`
2. Write a one-paragraph question to `<output_dir>/phase-context.md` (tag: `[ESCALATION]`)
3. Orchestrator detects BLOCKED status, reads the question, routes to oracle for a decision
4. Oracle appends decision to `<output_dir>/phase-context.md` (tag: `[DECISION]`)
5. Orchestrator re-dispatches forge with the decision injected into the envelope

## Completion Handling

After each agent completes:

1. Verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` matches task scope
3. Verify evidence exists for behavior changes (RED/GREEN)
4. `TaskUpdate(status: "completed")`
5. Scan TaskList for newly unblocked tasks → dispatch next batch immediately
6. Every 3 completed tasks: write summary to `<output_dir>/phase-context.md`

## Red Flags

- Dispatching an agent without a self-contained envelope (any field left blank without `N/A`)
- Dispatching agents for tasks with file conflicts without isolation
- Letting a forge agent "figure out" the file scope
- Running prism build in parallel with any forge write
- An agent that writes to a file it didn't declare in `File Scope`
