---
name: Ultrawork
version: "1.0.0"
description: This skill should be used when the user includes "ulw" or "ultrawork" in their prompt, or invokes /ulw. It provides fully autonomous, zero-gate execution: Intent Gate classifies the task, then the appropriate pipeline runs without any user approval steps. The ralph-loop keeps execution going until the task is 100% verified complete.
---

# Ultrawork (ULW)

Full-autonomous execution mode. Classify intent → execute pipeline → verify evidence → done. No approval gates. No stopping until finished.

## Activation Contract

This skill is invoked when:
1. The `ulw-detector` hook fires (user wrote `ulw` or `ultrawork` in their prompt), OR
2. The user explicitly calls `/ulw`

On activation:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

Then invoke the ralph-loop to ensure continuous execution:
```
Skill({ skill: "ralph-loop:ralph-loop", args: "Run until all tasks in the current session are completed and verified." })
```

## Step 1 — Intent Gate

**Before doing anything else, classify the user's true intent.** Do not take the literal words at face value.

Classify into one of:

| Intent | Signal words | Autonomous pipeline |
|---|---|---|
| `implement` | add, create, build, implement, write, make | Brainstorm(auto) → Plan(auto) → TDD impl → Review(auto) → Accept(auto) |
| `fix` | fix, broken, error, failing, bug, crash, 404, undefined, null | Systematic Debug → Fix → Verify |
| `refactor` | refactor, extract, rename, restructure, clean up, move | Brainstorm(auto) → Plan(auto) → Impl → Review(auto) |
| `research` | how does, what is, explain, compare, should I use, best practice | Scout → Report |
| `explain` | walk me through, describe, show me, what does X do | Read codebase → Structured answer |
| `test` | add tests, write tests, test coverage, unit test | testing-strategy → prism |

**Ambiguous signals**: if two intents are equally likely (e.g., "fix the tests" = fix _or_ test?), pick the one that involves the less destructive action first. Debug before patching.

**Never ask the user for clarification in ULW mode.** Make a decision and proceed. If you were wrong, you'll find out at the verification step and can course-correct.

## Step 2 — Pre-flight Checks

Before any code changes:
1. Read `workflow-state.json` to detect any in-progress work. If a workflow is mid-flight on a different task, warn in the output (do not block — record it).
2. Check the current git branch. If on `main`/`master`, create a feature branch automatically:
   ```bash
   git checkout -b ulw/$(date +%Y%m%d-%H%M%S)-<slug-from-task>
   ```
3. Record task intent and branch in `workflow-state.json`.

## Step 3 — Execute the Intent Pipeline

### Pipeline: `implement` / `refactor`

```
1. Brainstorm (auto-approve — no user confirmation)
   - Use brainstorming skill internally
   - Select the simplest approach that satisfies the stated requirements
   - Write 2-3 line design decision to phase-context.md
   - DO NOT present options to user

2. Plan (auto-approve)
   - Use writing-plans skill
   - Create atomic tasks with blockedBy dependencies
   - TaskCreate each task immediately
   - DO NOT show plan to user for approval

3. Implementation (DAG-aware, parallel)
   - For each unblocked task in TaskList:
     a. Apply testing-strategy: write failing test first (RED)
     b. Implement minimal change (GREEN)
     c. Refactor while tests stay green
     d. Run verification: bash -c "<test command>"
     e. Record evidence in verification-evidence.jsonl
   - Dispatch max 2 agents in parallel
   - Check for file conflicts before parallel dispatch

4. Review (auto — sentinel)
   - Invoke sentinel after each implementation batch
   - If APPROVE: continue
   - If REQUEST CHANGES: route back to implementer (max 3 loops, no user involved)
   - If NEEDS DISCUSSION after 3 loops: escalate to user with summary

5. Acceptance (auto — validator)
   - Invoke validator: reads plan, runs build+tests, checks feature delivery
   - If ACCEPT: TaskUpdate completed, continue
   - If REJECT: route back to implementer with gap list (max 2 loops)
   - If still REJECT after 2 loops: escalate to user
```

### Pipeline: `fix`

```
1. Apply systematic-debugging skill
   - Reproduce the bug with a minimal test case
   - Form a hypothesis
   - Verify hypothesis (do NOT patch before confirming root cause)

2. Write a failing test that captures the bug

3. Apply the fix (minimal change)

4. Run full verification suite

5. If tests pass: commit and report
6. If tests still fail: re-enter systematic-debugging (max 2 cycles)
7. After 2 cycles: escalate to user with full debug trace
```

### Pipeline: `research`

```
1. Invoke scout agent for web research + docs lookup
2. Synthesize findings
3. Report back — no code changes unless user follow-up
```

### Pipeline: `explain`

```
1. Read relevant codebase files
2. Trace execution flow
3. Structured written explanation — no code changes
```

### Pipeline: `test`

```
1. Apply testing-strategy skill
2. Invoke prism agent to write test suite
3. Run tests: verify RED → GREEN cycle
4. Report coverage and evidence
```

## Step 4 — Continuous Execution (ralph-loop)

The ralph-loop keeps this skill alive until the TaskList is empty:

```
while tasks_remaining():
    task = next_unblocked_task()
    execute(task)
    verify(task)
    TaskUpdate(task, status=completed)

if all_tasks_done() and verification_evidence_present():
    exit_loop()
else:
    continue_loop()
```

**Do NOT exit or declare done if:**
- Any task in TaskList is still `pending` or `in_progress`
- `verification-evidence.jsonl` has no entries for the current session
- The test suite has not been run since the last code change

## Step 5 — Verification Before Completion

After all tasks complete, apply `verification-before-completion`:

1. Run the full test suite — capture output
2. Run build / typecheck — capture output
3. Run lint — capture output
4. Write evidence to `verification-evidence.jsonl`
5. Compare deliverables against original task description

Only after step 4 is evidence written may you mark the workflow done.

## Error Recovery

| Error type | Action | Max retries |
|---|---|---|
| Syntax / type error | Auto-fix, re-run | 3 |
| Test failure | Re-enter implementation | 2 |
| Dependency error | `npm install` / `pip install`, retry | 2 |
| Logic / design error | Re-enter brainstorm with new constraint | 1 |
| Environment / infra error | Escalate to user immediately | 0 |
| Unknown | Investigate, then fix or escalate | 2 |

After max retries: **escalate**. Never loop infinitely on a failing task.

## ULW Golden Rules

1. **Classify intent first.** Never start working before the Intent Gate completes.
2. **Write the failing test first.** No exceptions, even in autonomous mode.
3. **Never claim done without evidence.** `verification-evidence.jsonl` must have fresh entries.
4. **Branch off main.** Never commit directly to `main`/`master` in ULW mode.
5. **Escalate, don't loop forever.** Max retries are hard limits — after that, report to user.
6. **Parallel max 2.** Dispatch at most 2 agents simultaneously. More creates context explosion.
7. **No feature creep.** Implement exactly what was asked. Spec compliance before code quality.

## Common Rationalizations — ULW Reality Check

| Rationalization | ULW Reality |
|---|---|
| "The user said ulw so I can skip tests" | No. Test-first is non-negotiable. ULW skips gates, not quality. |
| "I'll do a quick fix without debugging first" | No. For `fix` intent: reproduce → hypothesis → verify → patch. |
| "I can commit to main since it's autonomous" | No. Always branch. main is protected even in ULW mode. |
| "I should ask for clarification before proceeding" | No. Classify and decide. That's what ULW is for. |
| "The tests pass so I don't need to run lint" | No. Full verification suite: tests + build + lint. |

## Output Format

When ULW completes, report:

```
## ULW Complete ✓

**Intent classified:** implement
**Branch:** ulw/20260429-143022-add-divide-function
**Tasks completed:** 2/2

### What was done
- Added `divide(a, b)` to src/math.js with division-by-zero guard
- Added 4 tests in test/math.test.js

### Verification evidence
- Tests: 7 passed, 0 failed (npm test)
- Build: OK (tsc --noEmit)
- Lint: 0 warnings (eslint src/)

### Commits
- feat: add divide function with tests (abc1234)
```
