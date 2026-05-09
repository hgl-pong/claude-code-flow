---
name: Ultrawork
version: "1.3.0"
description: "Triggers when user includes ulw/ultrawork in prompt or invokes /ulw."
---

# Ultrawork (ULW)

Full-autonomous single-task execution. No approval gates. Stop Hook prevents exit until complete.

**Branch routing:** If activation context contains `ULI MODE ACTIVE` (injected by `uli-detector.py`), read `skills/ultrawork/ULI.md` and run the ULI branch. Otherwise continue below.

## Activation

Triggered by: `ulw-detector` hook (user wrote `ulw`/`ultrawork`), or `/ulw` invocation.

**Immediately on activation:**

1. Write ULW state file via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py ulw-init "<ORIGINAL_PROMPT>"`
2. Set workflow mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous`
3. Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan`
4. Derive a task slug (2–4 words kebab-case) from the task description; set via `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py ulw-set-task "<slug>"` — creates `.claude/flow/ulw/<slug>/`. All subsequent file writes for this task go inside this directory.

## Step 1 — Intent Gate

Classify the user's true intent (do not take literal words at face value):

| Intent | Signal words | Pipeline |
|---|---|---|
| `implement` | add, create, build, implement, write, make | Brainstorm→Plan→TDD→Review→Accept |
| `fix` | fix, broken, error, failing, bug, crash | Debug→Fix→Verify |
| `refactor` | refactor, extract, rename, restructure, clean up | Brainstorm→Plan→Impl→Review |
| `research` | how does, what is, explain, compare, best practice | Scout→Report |
| `explain` | walk me through, describe, show me | Read→Structured answer |
| `test` | add tests, write tests, test coverage, unit test | testing-strategy→prism |

Ambiguous signals: pick the less destructive action first. **Never ask for clarification in ULW mode** — decide and proceed.

Update state: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py ulw-set-intent <CLASSIFIED_INTENT>`

## Step 1b — Domain Detection + Gate Checklist

After classifying intent, detect the task domain using the same rules as `dev-orchestrator`:
- Does the task involve frontend files (`.tsx`, `.jsx`, `.vue`, `.svelte`, `.css`, `.scss`, `.html`)?
- Does the task involve UI components, pages, layouts, styling, or visual elements?
- Does the task involve user-facing interaction?

If ANY are true → task domain is **frontend-UI**.

Then evaluate the mandatory gates. In ULW autonomous mode, ALL gates are auto-approved, but they ALL must still RUN:

```
ULW GATE CHECKLIST (all gates auto-approve but all must execute):

[ ] Brainstorm — always for implement/refactor
[ ] Research (scout) — always for implement/refactor (auto-skip if pure internal)
[ ] Plan (oracle) — ALWAYS mandatory
[ ] Architecture (oracle) — mandatory when: new system, 3+ modules, cross-cutting change
[ ] UI Research (scout) — mandatory when task domain is frontend-UI
[ ] UI Design (ui-design skill) — mandatory when task domain is frontend-UI
[ ] Review (sentinel) — ALWAYS mandatory
[ ] Acceptance (prism) — ALWAYS mandatory
```

Record checked gates in `.claude/flow/ulw/<slug>/phase-context.md` under `## Gate Checklist`.

**CRITICAL: A checked gate MUST execute, even in autonomous mode. Auto-approve means no user confirmation needed, NOT that the gate is skipped.**

## Step 2 — Pre-flight

1. Read `workflow-state.json` for in-progress work. Warn if mid-flight (do not block).
2. If on `main`/`master`, branch off: `git checkout -b ulw/$(date +%Y%m%d-%H%M%S)-<slug>`

## Step 3 — Execute Intent Pipeline

After creating tasks with TaskCreate, update totals: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py ulw-set-total <N>`
After each task completes: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py ulw-inc-done`

### `implement` / `refactor`

1. Brainstorm (auto-approve) — select simplest approach, write 2-3 line decision to `.claude/flow/ulw/<slug>/phase-context.md`. Do NOT present options.
2. Research (auto-approve, if checked) — invoke scout for external info. Skip only for pure internal logic tasks.
3. Plan (auto-approve) — use `writing-plans` skill, create atomic tasks with blockedBy dependencies. Do NOT show plan.
4. Architecture (auto-approve, if checked) — oracle produces design. Append to `.claude/flow/ulw/<slug>/phase-context.md`.
5. UI Research (auto-approve, if checked) — scout researches design patterns. Write `.claude/flow/ulw/<slug>/ui-research.md`.
6. UI Design (auto-approve, if checked) — `ui-design` skill produces `DESIGN.md`. **forge MAY NOT be dispatched until DESIGN.md exists.**
7. Implementation (Ralph Loop + parallel scheduler):
   - **Ralph Loop**: each agent dispatch is stateless — self-contained prompt, no prior agent output carried forward. PICK → ENVELOPE → DISPATCH → WAIT → VERIFY → RECORD → LOOP.
   - **Parallel scheduler** (see dev-orchestrator Step 9): file conflict analysis, worktree isolation, dispatch non-conflicting agents in one message with `run_in_background: true`. Max 3 forge, 2 prism, 1 build.
   - Each agent prompt must use the **Context Envelope** format (Goal, Task, Dependencies, File Scope, Test Command, Acceptance Criteria, Constraints).
   - Each agent: test-first RED → implement GREEN → refactor → verify → record evidence → increment done.
8. Review (auto, sentinel — two-stage) — Stage 1: spec compliance → Stage 2: code quality (only if Stage 1 passes). APPROVE→continue; REQUEST CHANGES→back to implementer (max 3 loops); NEEDS DISCUSSION after 3 loops→escalate. Use subagent-driven review: dispatch sentinel with `review_focus: spec_compliance`, then a fresh sentinel with `review_focus: code_quality`.
9. Acceptance (auto, prism) — ACCEPT→TaskUpdate completed; REJECT→back to implementer with gap list (max 2 loops).

### `fix`

1. Apply `systematic-debugging` — reproduce, hypothesize, verify root cause. Do NOT patch before confirming.
2. Write failing test capturing the bug.
3. Apply minimal fix.
4. Full verification suite.
5. If still failing: re-enter debug (max 2 cycles), then escalate.

### `research`

Scout→synthesize→report. No code changes unless user follow-up.

### `explain`

Read codebase→trace flow→structured explanation. No code changes.

### `test`

Apply `testing-strategy`→prism writes suite→verify RED→GREEN→report coverage.

## Step 4 — Verification Before Completion

After all tasks: run full test suite + build + lint. Write evidence to `verification-evidence.jsonl`. Compare deliverables against original task. Only after evidence is written may you signal completion.

## Step 5 — Signal Completion (REQUIRED)

Output the completion tag as the **last thing in your final message**:

```
<ulw-done>BRIEF_SUMMARY_OF_WHAT_WAS_DONE</ulw-done>
```

Rules:
- Only output when ALL tasks have fresh verification evidence
- The summary must be truthful — the Stop Hook trusts this tag
- Do NOT output speculatively or prematurely

## Error Recovery

| Error type | Action | Max retries |
|---|---|---|
| Syntax / type error | Auto-fix, re-run | 3 |
| Test failure | Re-enter implementation | 2 |
| Dependency error | Install, retry | 2 |
| Logic / design error | Re-enter brainstorm with new constraint | 1 |
| Environment / infra error | Escalate to user immediately | 0 |
| Unknown | Investigate, then fix or escalate | 2 |

After max retries: **escalate**. Never loop infinitely.

## ULW Golden Rules

1. **Write ulw-state.json first** — Stop Hook needs it.
2. **Classify intent first** — never start before Intent Gate completes.
3. **Detect domain and evaluate gate checklist** — every checked gate MUST execute.
4. **Write the failing test first** — no exceptions, even in autonomous mode.
5. **Never emit `<ulw-done>` without evidence** — the Stop Hook trusts this tag.
6. **Branch off main** — never commit directly to `main`/`master`.
7. **Escalate, don't loop forever** — max retries are hard limits.
8. **Dynamic parallelism** — dispatch up to 3 forge, 2 prism, 1 build. Use worktree isolation for file conflicts.
9. **No feature creep** — implement exactly what was asked.
10. **Ralph Loop: stateless dispatch** — every agent prompt is self-contained. Never carry prior agent output into the next dispatch.
11. **Auto-approve does not mean skip** — autonomous mode skips user confirmation, NOT gate execution.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I'm 90% done, close enough to emit `<ulw-done>`" | 90% is not 100%. The remaining 10% is what the user asked for. |
| "The tests are flaky, not my fault" | Flaky tests are your problem in autonomous mode. Fix or isolate them. |
| "I'll verify in the next iteration" | There is no next iteration. Verify now. |
| "The remaining task is trivial" | Trivial means one file, not skippable. Do it. |
| "I ran out of retries" | Escalate. Never silently skip. |
| "This frontend task doesn't need ui-design skill" | If Gate Checklist checked UI Design, run it. No exceptions. |
| "Auto-approve means I can skip this gate" | Auto-approve means no user prompt. The gate still executes. |
