# Task Decomposition Patterns

Oracle uses these patterns when writing plans for large tasks.

## Feature (new behavior)

```
Task 1: Types/interfaces            [forge]  no deps
Task 2: Backend implementation      [forge]  blockedBy: [1]
Task 3: Frontend implementation     [forge]  blockedBy: [1]
Task 4: Tests — unit                [prism]  blockedBy: [2, 3]
Task 5: Tests — integration         [prism]  blockedBy: [4]
Task 6: Review                      [sentinel] blockedBy: [5]
```

Tasks 2 and 3 run in parallel (both blocked by 1, no file overlap).

## Refactor (restructure without behavior change)

```
Task 1: Impact analysis             [research]  no deps
Task 2: Core structural changes     [forge]  blockedBy: [1], sequential batches
Task 3: Update callers              [forge]  blockedBy: [2], parallel if caller files disjoint
Task 4: Regression tests            [prism]  blockedBy: [all forge]
Task 5: Review                      [sentinel] blockedBy: [4]
```

## Bug Fix (unknown cause)

```
Task 1: Write failing test          [prism]  no deps
Task 2: Root cause + fix            [forge]  blockedBy: [1]
Task 3: Verify + run suite          [prism]  blockedBy: [2]
Task 4: Review (optional)           [sentinel] blockedBy: [3]
```

## Large Task (complex, many files)

Split when a task needs **multiple independent verification commands** — each verifiable piece becomes its own task.

```
Batch A (parallel): tasks with disjoint write sets, each independently verifiable
Batch B (sequential): tasks whose verification depends on Batch A's output existing
Batch C (parallel with B if no write conflicts): additional independent verifiable units
Batch D: integration verification  [prism]  blockedBy: [all impl batches]
Batch E: review                    [sentinel] blockedBy: [D]
```

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
