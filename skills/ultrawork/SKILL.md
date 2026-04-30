---
name: Ultrawork
version: "1.2.0"
description: This skill should be used when the user includes "ulw", "ultrawork", or "uli" in their prompt, or invokes /ulw or /uli. ULW provides fully autonomous single-task execution. ULI (Ultra Loop Iteration) provides fully autonomous product iteration: a PD agent proposes requirements each cycle, the dev pipeline executes, hard acceptance validates, and the loop continues until max_iterations or product goal is reached.
---

# Ultrawork (ULW) + Ultra Loop Iteration (ULI)

Two modes, one skill.

- **ULW**: single task → classify intent → execute pipeline → verify → `<ulw-done>`
- **ULI**: product loop → PD proposes → dev executes → hard acceptance → next iteration → `<uli-done>`

**Which branch to run:** If the activation context contains `ULI MODE ACTIVE` (injected by `uli-detector.py`), run the **ULI branch** (below). Otherwise run the **ULW branch** (original pipeline).

Full-autonomous execution mode. No approval gates. Stop Hook prevents exit until complete.

## How Continuous Execution Is Guaranteed

ULW uses a dedicated **Stop Hook** (`hooks/scripts/ulw-stop-hook.sh`) — not just a skill instruction. When Claude tries to exit:

1. The hook reads `.claude/flow/ulw-state.json`
2. If `active: true` and the last assistant message lacks `<ulw-done>`, the hook **blocks the exit** (`decision: "block"`) and re-injects the original prompt
3. Claude resumes work with full awareness of what it already did (files on disk, git history, task state)
4. This loop repeats until Claude outputs `<ulw-done>SUMMARY</ulw-done>` with verified evidence

This is the **Ralph Wiggum technique** — the hook, not the model, enforces completion.

## Activation Contract

This skill is invoked when:
1. The `ulw-detector` hook fires (user wrote `ulw` or `ultrawork` in their prompt), OR
2. The user explicitly calls `/ulw`

**Immediately on activation, write the ULW state file:**

```bash
python -c "
import json, os, datetime
state_dir = '.claude/flow'
os.makedirs(state_dir, exist_ok=True)
state = {
  'active': True,
  'session_id': os.environ.get('CLAUDE_SESSION_ID', ''),
  'intent': 'unknown',
  'prompt': '''ORIGINAL_PROMPT_HERE''',
  'task_done': 0,
  'task_total': 0,
  'iteration': 0,
  'max_iterations': 25,
  'started_at': datetime.datetime.utcnow().isoformat() + 'Z'
}
with open(os.path.join(state_dir, 'ulw-state.json'), 'w') as f:
    json.dump(state, f, indent=2)
"
```

Replace `ORIGINAL_PROMPT_HERE` with the **exact text of the user's original request** (used by the Stop Hook to re-inject if Claude exits early).

Then set workflow mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
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

**Ambiguous signals**: pick the less destructive action first. Debug before patching.

**Never ask the user for clarification in ULW mode.** Make a decision and proceed.

**After classifying, update ulw-state.json with the intent:**
```bash
python -c "
import json
with open('.claude/flow/ulw-state.json') as f: s = json.load(f)
s['intent'] = 'CLASSIFIED_INTENT_HERE'
with open('.claude/flow/ulw-state.json', 'w') as f: json.dump(s, f, indent=2)
"
```

## Step 2 — Pre-flight Checks

Before any code changes:
1. Read `workflow-state.json` to detect any in-progress work. If a workflow is mid-flight on a different task, warn in the output (do not block — record it).
2. Check the current git branch. If on `main`/`master`, create a feature branch automatically:
   ```bash
   git checkout -b ulw/$(date +%Y%m%d-%H%M%S)-<slug-from-task>
   ```

## Step 3 — Execute the Intent Pipeline

**After creating tasks with TaskCreate, update the total count in ulw-state.json:**
```bash
python -c "
import json
with open('.claude/flow/ulw-state.json') as f: s = json.load(f)
s['task_total'] = TOTAL_COUNT_HERE
with open('.claude/flow/ulw-state.json', 'w') as f: json.dump(s, f, indent=2)
"
```

**After each task completes, increment task_done:**
```bash
python -c "
import json
with open('.claude/flow/ulw-state.json') as f: s = json.load(f)
s['task_done'] = s.get('task_done', 0) + 1
with open('.claude/flow/ulw-state.json', 'w') as f: json.dump(s, f, indent=2)
"
```

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
   - Update ulw-state.json task_total
   - DO NOT show plan to user for approval

3. Implementation (DAG-aware, parallel)
   - For each unblocked task in TaskList:
     a. Apply testing-strategy: write failing test first (RED)
     b. Implement minimal change (GREEN)
     c. Refactor while tests stay green
     d. Run verification: bash -c "<test command>"
     e. Record evidence in verification-evidence.jsonl
     f. Increment ulw-state.json task_done
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

## Step 4 — Verification Before Completion

After all tasks complete, apply `verification-before-completion`:

1. Run the full test suite — capture output
2. Run build / typecheck — capture output
3. Run lint — capture output
4. Write evidence to `verification-evidence.jsonl`
5. Compare deliverables against original task description

Only after step 4 is evidence written may you signal completion.

## Step 5 — Signal Completion (REQUIRED)

**This is what stops the Stop Hook loop.**

After verification passes, output the completion tag in your final message:

```
<ulw-done>BRIEF_SUMMARY_OF_WHAT_WAS_DONE</ulw-done>
```

Example:
```
<ulw-done>Added divide(a,b) to src/math.js with division-by-zero guard. 7 tests pass. Build OK. Lint clean.</ulw-done>
```

**Rules:**
- Include this tag ONLY when ALL tasks have fresh verification evidence
- The summary must be truthful — the Stop Hook checks this tag to release the loop
- Do NOT output this tag speculatively or prematurely
- If you output this and the Stop Hook reads it, the loop ends — make sure work is actually done

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

1. **Write ulw-state.json first.** The Stop Hook needs it to work. Write it before doing anything else.
2. **Classify intent first.** Never start working before the Intent Gate completes.
3. **Write the failing test first.** No exceptions, even in autonomous mode.
4. **Never emit `<ulw-done>` without evidence.** The Stop Hook trusts this tag — don't lie.
5. **Branch off main.** Never commit directly to `main`/`master` in ULW mode.
6. **Escalate, don't loop forever.** Max retries are hard limits — after that, report to user.
7. **Parallel max 2.** Dispatch at most 2 agents simultaneously.
8. **No feature creep.** Implement exactly what was asked.

## Common Rationalizations — ULW Reality Check

| Rationalization | ULW Reality |
|---|---|
| "The user said ulw so I can skip tests" | No. Test-first is non-negotiable. ULW skips gates, not quality. |
| "I'll do a quick fix without debugging first" | No. For `fix` intent: reproduce → hypothesis → verify → patch. |
| "I can commit to main since it's autonomous" | No. Always branch. main is protected even in ULW mode. |
| "I should ask for clarification before proceeding" | No. Classify and decide. That's what ULW is for. |
| "The tests pass so I don't need to run lint" | No. Full verification suite: tests + build + lint. |
| "I can output `<ulw-done>` to stop early" | No. Only output when ALL tasks are verified. The hook trusts that tag. |

## Output Format

When ULW completes, the final message must include:

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

<ulw-done>Added divide(a,b) to src/math.js with guard. 7 tests pass. Build OK. Lint clean.</ulw-done>
```

The `<ulw-done>` tag must be the last thing in the message.

---

# ULI — Ultra Loop Iteration Branch

> **Enter this branch when:** activation context contains `ULI MODE ACTIVE` (injected by `uli-detector.py`).

ULI is a continuous product iteration loop. Unlike ULW which executes a single task, ULI runs `N` iterations where each iteration is: **PD proposes requirements → dev pipeline executes → hard acceptance validates → next iteration**.

## ULI Stop Hook

`hooks/scripts/uli-stop-hook.sh` blocks exit until `<uli-done>` is emitted. It reads `uli-state.json`, checks `current_phase`, and re-injects a phase-aware continuation prompt. The same "Ralph Wiggum technique" as ULW — the hook, not the model, enforces completion.

## ULI Step 0 — Initialize

**Immediately on activation, write the ULI state file:**

```bash
python -c "
import json, os, datetime
state_dir = '.claude/flow'
os.makedirs(state_dir, exist_ok=True)
# Extract goal from the user's prompt (everything after 'uli ')
goal = 'GOAL_FROM_USER_PROMPT'
state = {
  'active': True,
  'session_id': os.environ.get('CLAUDE_SESSION_ID', ''),
  'goal': goal,
  'iteration': 1,
  'max_iterations': 10,
  'current_phase': 'pd_generating',
  'pd_proposal_ready': False,
  'acceptance_status': None,
  'started_at': datetime.datetime.utcnow().isoformat() + 'Z',
  'last_iteration_at': None
}
with open(os.path.join(state_dir, 'uli-state.json'), 'w') as f:
    json.dump(state, f, indent=2)
"
```

Replace `GOAL_FROM_USER_PROMPT` with the product goal from the user's message (everything after "uli").

Then set workflow mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

**Create/verify `.claude/flow/product-state.md`:**
- If it already exists: read it to understand the product goal and completed features.
- If it does not exist: create it from the user's ULI goal + README context:

```markdown
# Product State

## Goal
<goal from user's uli prompt>

## Completed Features
(none yet)

## Known Gaps / Deferred
(none yet)
```

**Branch off main:**
```bash
git checkout -b uli/$(date +%Y%m%d-%H%M%S)-iteration-loop
```

## ULI Step 1 — Start Iteration (repeat for each iteration)

Update state to mark iteration start:
```bash
python -c "
import json
with open('.claude/flow/uli-state.json') as f: s = json.load(f)
s['current_phase'] = 'pd_generating'
s['pd_proposal_ready'] = False
s['acceptance_status'] = None
with open('.claude/flow/uli-state.json', 'w') as f: json.dump(s, f, indent=2)
"
```

## ULI Step 2 — PD Agent (parallel with nothing — runs first)

Spawn the PD agent to generate this iteration's requirements:

```
Agent({
  name: "pd",
  subagent_type: "claude-code-flow:pd",
  model: "sonnet",
  prompt: "Generate requirements for ULI iteration N. Goal: <goal>. Read .claude/flow/product-state.md and .claude/flow/uli-acceptance-report.md (if it exists). Output proposal to .claude/flow/uli-proposal.md. See agents/pd.md for the required format."
})
```

Wait for PD to complete. Then:
1. Read `.claude/flow/uli-proposal.md`
2. Verify it has at least 1 CORE requirement with a concrete acceptance criterion
3. Update state: `pd_proposal_ready = true`, `current_phase = "dev_pipeline"`

If PD produces no CORE requirements or produces untestable requirements (e.g., "improve UX"), stop ULI and report to user: the PD agent could not generate actionable requirements.

## ULI Step 3 — Dev Pipeline

Run the standard dev pipeline against the PD's requirements. This is the same pipeline as `dev-orchestrator` autonomous mode, with the PD proposal as the input spec instead of a user-approved plan.

```
Current phase: dev_pipeline

1. oracle (auto) — read uli-proposal.md, decompose CORE requirements into tasks
   - Create tasks via TaskCreate (subject, description, files, acceptance criteria, blockedBy)
   - Write agent brief to .claude/plans/plan-brief.md
   - DO NOT show plan to user

2. Implementation (DAG-aware, parallel, max 2 agents)
   - For each unblocked task:
     a. testing-strategy: write failing test first (RED)
     b. Implement minimal change (GREEN)
     c. Refactor while tests stay green
     d. Record evidence in verification-evidence.jsonl
   - Frontend tasks → weaver; backend/general → forge; tests → prism; build → anvil

3. Sentinel review (auto)
   - If APPROVE: continue to acceptance
   - If REQUEST CHANGES: route back to implementer (max 2 loops)
   - If still failing after 2 loops: mark acceptance_status = "sentinel_failed", skip to Step 4

4. Update state: current_phase = "acceptance"
```

## ULI Step 4 — Hard Acceptance Gate

**This gate is strict. Partial acceptance does NOT advance the iteration.**

Invoke validator agent:
```
Agent({
  name: "validator",
  subagent_type: "claude-code-flow:validator",
  prompt: "Run acceptance validation for ULI iteration N. Read .claude/plans/plan-brief.md for requirements. Run: (1) build, (2) full test suite, (3) verify each CORE requirement from uli-proposal.md is delivered. Produce ACCEPT or REJECT verdict with gap list."
})
```

**ACCEPT** (ALL must be true):
- Build passes
- All tests pass
- Every CORE requirement from `uli-proposal.md` has a verified acceptance criterion met

On ACCEPT:
```bash
# 1. Write acceptance report
cat > .claude/flow/uli-acceptance-report.md << 'EOF'
# Iteration N Acceptance Report
**Verdict:** ACCEPT
**Date:** <timestamp>

## Requirements Verified
- [PASS] <requirement 1> — <evidence>
- [PASS] <requirement 2> — <evidence>

## Test Results
- Tests: X passed, 0 failed
- Build: OK

## Commits This Iteration
- <commit hash> <message>
EOF

# 2. Update product-state.md — append completed features
# 3. Commit: "feat(uli-N): <iteration goal>"
# 4. Update uli-state.json: iteration++, acceptance_status = "accepted"
# 5. Proceed to next iteration (go back to Step 1)
```

**REJECT** (any of: build fails, tests fail, any CORE requirement unmet):

On REJECT (first time): route back to implementer with the gap list (max 2 retry loops):
- Update state: `current_phase = "dev_pipeline"`
- Pass gap list to forge/weaver as additional context
- Re-run from Step 3

On REJECT (after 2 retries): **stop ULI and escalate to user**:
```
Write .claude/flow/uli-acceptance-report.md with REJECT verdict and gap list.
Update uli-state.json: active = false, acceptance_status = "rejected_after_retries"
Report to user: "ULI iteration N could not pass acceptance after 2 retries. Gaps: <list>."
Do NOT emit <uli-done> — let the user decide how to proceed.
```

## ULI Step 5 — Iteration Complete, Check Loop Condition

After ACCEPT, check whether to continue:

```python
# Read uli-state.json
iteration = state['iteration']
max_iterations = state['max_iterations']

if iteration >= max_iterations:
    # Max iterations reached — emit <uli-done>
    proceed to Step 6
else:
    # More iterations available — go back to Step 1
    iteration += 1
    update uli-state.json
    go to Step 1
```

**Optionally check if the product goal is "done":** After each ACCEPT, re-read the product goal and the completed features list. If all major goals are covered, emit `<uli-done>` even before max_iterations.

## ULI Step 6 — Signal Completion

After all iterations complete (or goal achieved):

Apply `verification-before-completion` one final time across all delivered features.

Then output:

```
## ULI Complete

**Goal:** <product goal>
**Iterations completed:** N/max_iterations
**Branch:** uli/...

### What was delivered
- [Iteration 1] <feature> (commit: abc1234)
- [Iteration 2] <feature> (commit: def5678)
- ...

### Final verification
- Tests: X passed, 0 failed
- Build: OK
- Lint: clean

### Product state
See .claude/flow/product-state.md for full feature inventory.

<uli-done>Delivered N features over M iterations: <brief summary>. All tests pass. Build OK.</uli-done>
```

The `<uli-done>` tag must be the last thing in the message.

## ULI State Transitions

```
initialized
    → pd_generating   (Step 2: PD agent running)
    → dev_pipeline    (Step 3: oracle + forge/weaver/prism executing)
    → acceptance      (Step 4: validator running)
    → complete        (ACCEPT: iteration done, loop continues or ends)
    → escalated       (REJECT after retries: stopped, user must intervene)
```

## ULI Golden Rules

1. **Write uli-state.json first.** The Stop Hook needs it to work.
2. **PD runs before dev.** Never start the dev pipeline without a proposal in `uli-proposal.md`.
3. **Hard acceptance, not soft.** Build + tests + feature checklist ALL must pass. One failure = REJECT.
4. **REJECT after retries = escalate, not loop.** Never retry more than 2 times per iteration.
5. **Never emit `<uli-done>` after a REJECT.** Only on full iteration success.
6. **Branch off main.** Never commit directly to `main`/`master`.
7. **Update product-state.md after each ACCEPT.** PD needs this for the next iteration.
8. **No feature creep from PD.** PD proposes, dev delivers exactly that. No extras.

## Common Rationalizations — ULI Reality Check

| Rationalization | ULI Reality |
|---|---|
| "The acceptance was close enough, I'll advance" | No. Hard acceptance means ALL criteria pass. Close is REJECT. |
| "PD's requirements are vague but I'll guess" | No. Untestable requirements → stop and report. PD must rewrite. |
| "I'll skip the PD agent and implement directly" | No. PD runs every iteration. That's the point of ULI. |
| "The tests pass so the acceptance must pass" | No. Acceptance also checks feature delivery against proposal. Both must pass. |
| "I can emit <uli-done> after a REJECT escalation" | No. <uli-done> means success. REJECT after retries means stop without <uli-done>. |
