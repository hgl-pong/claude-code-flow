---
name: Planning
version: "1.0.0"
description: "Use for writing and executing implementation plans. Triggers on 'write a plan', 'plan this feature', 'create tasks for', 'execute the plan', 'run the plan', or when you have an approved spec or requirements for a multi-step task before touching code."
argument-hint: "<feature to plan or plan to execute>"
---

# Planning

Write executable plans and drive them to completion. Two phases: **write** the plan, then **execute** the plan.

## Iron Law

**NO PLACEHOLDERS. NO VAGUE INSTRUCTIONS. EVERY TASK STANDS ALONE.**

A plan is written for a fresh agent with zero project context and zero ability to "figure it out." If a task cannot be executed by reading it alone, the plan is incomplete.

## Phase 1: Write Plan

### Process

1. Read the approved spec or requirements.
2. Map files to responsibilities — design units with clear boundaries.
3. Split work into small test-first tasks (each step is 2-5 minutes).
4. Add exact commands and expected results. No "TBD", "TODO", "implement later".
5. Run the self-review checklist below.
6. **Plan Review Gate (mandatory, two phases)**:
   - Phase 1: Self-review — run the checklist below, fix any issues.
   - Phase 2: Present plan to user for approval. No implementation until approved.
   - If user requests changes: revise, repeat both phases.

Self-review checklist:

1. Map each requirement to at least one task.
2. Search for placeholders and vague instructions.
3. Check type names, function names, command names, file paths for consistency.
4. Confirm task order respects dependencies — no cycles, no false blocks.
5. Verify no file conflicts between parallel tasks.
6. Verify every task has a concrete test command and expected output.

### Plan Header

```markdown
# <Feature Name> Implementation Plan

**Goal:** <one sentence>
**Architecture:** <2-3 sentence summary>
**Verification:** <main commands and acceptance checks>

## Decisions
- <decision>: <rationale>

## Rejected Alternatives
- <alternative>: <why rejected>

## Risks
- <risk>: <mitigation>
```

### Task Shape

Each task must be independently understandable:

```markdown
### Task N: <name>

**Agent:** forge | prism | sentinel | research
**BlockedBy:** [task IDs] | none
**Files:**
- Create: `path/to/new-file`
- Modify: `path/to/existing-file`
- Test: `path/to/test-file`

- [ ] Step 1: Write the failing test
  - Command: `<exact test command>`
  - Expected failure: `<specific failure>`
- [ ] Step 2: Implement the smallest change
- [ ] Step 3: Run focused tests
- [ ] Step 4: Run broader verification if needed
- [ ] Step 5: Review and record evidence
```

**Agent assignment:**
- `forge` — file creation/modification
- `prism` — test runs, build verification, acceptance
- `sentinel` — review only; always after prism
- `research` — analysis; writes only output files

**BlockedBy rules:** only add a true data dependency. "Task B needs Task A's output file" → blocked. "Same module" → NOT a reason to block; check file conflict instead.

### Bite-Sized Granularity

Each step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code" — step
- "Run the tests" — step
- "Commit" — step

### Quality Bar

- Exact file paths.
- Exact commands.
- Expected output for tests.
- No placeholders.
- No "similar to previous task"; repeat details.
- Each task has one verification command that proves it done.

## Phase 2: Execute Plan

### Process

1. Read plan file.
2. Review critically — identify questions or concerns.
3. If concerns: raise with user before starting.
4. Create TaskCreate for all tasks.
5. Execute each task: follow steps exactly, run verifications as specified.
6. Use prompt templates from `dev-orchestrator/references/subagent-prompts.md` for agent dispatch.
7. When all tasks verified, invoke `dev-orchestrator` finish-branch phase.

### When to Stop

**STOP immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing progress
- Don't understand an instruction

**Ask for clarification rather than guessing.**

### Prompt Requirements

Every dispatch must include:
- Goal, task, working directory, completed dependencies, exact file scope
- Exact test command and acceptance criteria
- Relevant plan/design/code excerpts (paste directly — never ask subagents to "read the plan")
- Explicit out-of-scope files or behaviors
- Required `FILES_MODIFIED` declaration

## Plan Location

Persist in structured workflow state first:

- `.claude/flow/plan-state.json`
- `.claude/flow/workflow-state.json`

Export `.claude/flow/plans/<task-slug>/plan-brief.md` as agent-readable brief when needed.

## Handoff

Every task must be convertible into a context envelope for the orchestrator: goal, exact task, working directory, completed dependencies, file scope, test command, acceptance criteria, relevant excerpts, constraints, and out-of-scope boundaries. The source of truth is the approved plan/spec plus `<output_dir>/phase-context.md`; do not rely on chat history.

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "The developer can figure it out" | If they could, they wouldn't need a plan. Be explicit. |
| "Similar to the previous task" | Similar is not identical. Repeat the details. |
| "I'll add TODOs for the tricky parts" | TODOs in a plan mean the plan is not done. |
| "The file path is obvious from context" | Context is what the plan creates. Write every path explicitly. |
| "I'll skip the test command, it's standard" | Standards vary. Write it. |

## Red Flags — STOP

- "They'll know what I mean"
- "I'll skip the test command, it's standard"
- "I'll just reference the design doc"
- "The exact file doesn't matter at this stage"
- Skipping a verification step because "it's obvious"
- Adapting the plan without discussing with user
- Proceeding when blocked instead of asking for help
- Trusting agent success reports without checking FILES_MODIFIED
