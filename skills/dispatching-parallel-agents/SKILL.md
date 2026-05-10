---
name: Dispatching Parallel Agents
version: "2.1.0"
description: "Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies"
argument-hint: "<tasks to dispatch>"
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
| research (general-purpose) | unlimited | read-only, no conflicts |

## Completion Handling

After each agent completes:

1. Verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` matches task scope
3. Verify evidence exists for behavior changes (RED/GREEN)
4. `TaskUpdate(status: "completed")`
5. Scan TaskList for newly unblocked tasks → dispatch next batch immediately
6. Every 3 completed tasks: write summary to `<output_dir>/phase-context.md`

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

## Reference

For decomposition patterns (feature, refactor, bug fix, large task) and inter-agent handoff protocols see `decomposition-patterns.md` in this directory.
