# ULI — Ultra Loop Iteration Branch

> Enter this branch when activation context contains `ULI MODE ACTIVE`.

ULI is a continuous product iteration loop. Each iteration is an **atomic unit**: **PD proposes a new PRD → full dev pipeline delivers ALL of it → hard acceptance validates the whole iteration → commit → next iteration**.

One iteration = one PD proposal = one git commit = one entry in product-state.md.

## IRON LAW

**HARD ACCEPTANCE IS NON-NEGOTIABLE. BUILD + TESTS + FEATURE CHECKLIST ALL MUST PASS. ONE FAILURE = REJECT.**

Partial delivery does not advance the iteration. Shipping broken features is worse than shipping nothing.

**ONE ITERATION = ONE PD PROPOSAL.** Do not split a PD proposal across iterations. Do not treat individual tasks as iterations.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "8 out of 10 tests pass, close enough" | 8/10 is REJECT. The 2 failing tests may catch critical bugs. |
| "The failing test is flaky, not my code" | Flaky tests are your problem in ULI. Fix or isolate them. |
| "The feature works, just missing edge cases" | Missing edge cases means the feature does not work. REJECT. |
| "I'll fix it in the next iteration" | Next iteration is for new features, not fixing this iteration's failures. |
| "Acceptance is too strict" | Strict acceptance is what makes ULI produce quality. Soften it and you get tech debt. |
| "PD's requirement was unclear" | Unclear requirements get rejected at PD review, not at acceptance. Go back to PD. |
| "This task is small enough to count as one iteration" | A task is not an iteration. PD proposal → full delivery → acceptance = one iteration. |
| "I'll just do one task and loop" | The loop is PD→deliver→accept→loop. Not task→loop. |

### Red Flags — STOP the iteration and escalate if:

- PD proposal has no executable acceptance criteria
- Same feature rejected 3+ times across iterations
- Sentinel finds the same class of issue repeatedly
- Build fails twice in a row for different reasons
- No new code committed in 2+ iterations

## Iteration Document Structure

Each iteration stores artifacts in a folder named by a short English slug derived from its goal:

```
.claude/flow/uli/
├── product-state.md              # Shared across all iterations — goal + cumulative features
├── <task-slug>/                  # e.g. "add-auth", "fix-login", "build-test-suite"
│   ├── proposal.md               # PD requirements proposal (PRD for this iteration)
│   ├── analysis.md               # Scout product analysis
│   ├── plan.md                   # Oracle implementation plan
│   ├── plan-brief.md             # Agent-readable brief
│   └── acceptance-report.md     # Acceptance verdict + evidence
└── <next-task-slug>/
    └── ...
```

**Slug derivation:** at the start of each iteration, derive a 2–4 word kebab-case slug from the iteration goal (e.g., "add user auth" → `add-user-auth`). Store it in `uli-state.json` as `current_task_slug`. All agents in this iteration receive the slug via their Context Envelope and use it to construct paths.

## ULI Stop Hook

`uli-stop-hook.sh` blocks exit until `<uli-done>` is emitted. Same "Ralph Wiggum technique" as ULW — the hook enforces completion.

## Step 0 — Initialize

1. Write ULI state file via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-init "<GOAL_FROM_USER_PROMPT>"` (default: max_iterations=10)
2. Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous`
3. Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan`
4. Create/verify `.claude/flow/uli/product-state.md` (goal + completed features + known gaps).
5. Derive iteration-1 slug from the first iteration's expected goal (kebab-case, 2–4 words). Set via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-set-task "<slug>"`; creates `.claude/flow/uli/<slug>/`.
6. Branch off main: `git checkout -b uli/$(date +%Y%m%d-%H%M%S)-iteration-loop`

## Iteration Loop (Steps 1-5, repeat until max_iterations or goal achieved)

Each pass through this loop is ONE iteration. The iteration number increments ONLY after acceptance passes and a commit is made.

```
┌─────────────────────────────────────────────┐
│  Step 1: PD Agent — generate proposal.md    │
│           (MUST produce new PRD each time)   │
├─────────────────────────────────────────────┤
│  Step 2: Oracle — plan ALL tasks for this    │
│           iteration from the proposal        │
├─────────────────────────────────────────────┤
│  Step 3: Implement ALL tasks                 │
│           (Ralph Loop, parallel scheduler)    │
├─────────────────────────────────────────────┤
│  Step 4: Sentinel review (two-stage)         │
├─────────────────────────────────────────────┤
│  Step 5: Hard acceptance gate                │
│           ACCEPT → commit → increment → loop │
│           REJECT → fix → re-accept (max 2)   │
└─────────────────────────────────────────────┘
```

### Step 1 — Product Analysis + Proposal (MUST run every iteration)

**1a. Scout analyzes product state:**

Update state: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-set-phase pd_generating`

```
Agent({
  name: "scout",
  subagent_type: "claude-code-flow:scout",
  model: "sonnet",
  prompt: """
## Envelope
- **Goal:** <product goal>
- **Your Task:** Analyze product state and recommend next iteration priorities.
- **Iteration:** N / max_iterations
- **Completed Features:** <read from .claude/flow/uli/product-state.md>
- **Last Verdict:** <read from .claude/flow/uli/<slug>/acceptance-report.md, may not exist>
- **Task Slug:** <slug>

Read .claude/flow/uli/product-state.md, .claude/flow/uli/<slug>/acceptance-report.md, recent git log, and project README.
Write analysis to .claude/flow/uli/<slug>/analysis.md with: product state summary, gap analysis, top 3 recommended areas with rationale.
"""
})
```

Wait for scout. Read `.claude/flow/uli/<slug>/analysis.md`.

**1b. Oracle proposes requirements:**

```
Agent({
  name: "oracle",
  subagent_type: "claude-code-flow:oracle",
  model: "opus",
  prompt: """
## Envelope
- **Goal:** <product goal>
- **Your Task:** Propose requirements for iteration N based on the product analysis.
- **Iteration:** N / max_iterations
- **Product Analysis:** <read from .claude/flow/uli/<slug>/analysis.md>
- **Constraints:** Max 3 CORE, every CORE must have concrete, executable acceptance criterion.

Output to .claude/flow/uli/<slug>/proposal.md.
"""
})
```

Wait for oracle. Read `.claude/flow/uli/<slug>/proposal.md`. Verify at least 1 CORE requirement with concrete acceptance criterion. If none or untestable, stop ULI and report to user.

**VERIFY:** `.claude/flow/uli/<slug>/proposal.md` exists and contains at least 1 CORE requirement. If not, STOP.

Update state: `uli-set-phase dev_pipeline`

### Step 2 — Oracle Plan (ALL tasks for this iteration)

Oracle reads `.claude/flow/uli/<slug>/proposal.md` and decomposes it into ALL tasks needed for this iteration.

1. Oracle creates tasks via `TaskCreate` with `blockedBy` dependencies
2. Writes implementation plan to `.claude/flow/uli/<slug>/plan.md`
3. Writes agent brief to `.claude/flow/uli/<slug>/plan-brief.md`
4. Sets total tasks: `flow-state.py ulw-set-total <N>`

**VERIFY:** `.claude/flow/uli/<slug>/plan-brief.md` exists and TaskList shows all tasks for this iteration. Every CORE requirement from the proposal maps to at least one task.

Do NOT show plan to user (autonomous mode).

### Step 3 — Implementation (Ralph Loop + Parallel Scheduler)

**Ralph Loop**: each agent dispatch is stateless — self-contained prompt via Context Envelope, no prior agent output carried forward. PICK → ENVELOPE → DISPATCH → WAIT → VERIFY → RECORD → LOOP.

Use parallel scheduler (see dev-orchestrator): file conflict analysis, worktree isolation for conflicting tasks, dispatch non-conflicting agents in a single message with `run_in_background: true`. Max 3 parallel for forge, 2 for prism (unit/integration), 1 for prism (build). Every agent prompt must use the **Context Envelope** format.

Test-first RED→GREEN→refactor→record evidence. All code→forge; tests/build/acceptance→prism.

**IMPORTANT:** The Ralph Loop processes ALL tasks for this iteration. Do NOT advance to Step 4 until ALL tasks are done or escalated. The loop runs tasks, not iterations.

After every task completes: `flow-state.py ulw-inc-done`

**VERIFY:** TaskList shows all tasks completed. All tasks have verification evidence.

### Step 4 — Sentinel Review (two-stage)

**Stage 1: Spec Compliance** — does implementation match the proposal? Check every CORE requirement from `.claude/flow/uli/<slug>/proposal.md`.
**Stage 2: Code Quality** — only runs if Stage 1 passes. Check naming, structure, error handling, test coverage.

APPROVE→Step 5; REQUEST CHANGES→back to Step 3 implementer (max 2 loops); still failing→Step 5 with `acceptance_status = "sentinel_failed"`.

Use subagent-driven review: dispatch sentinel with `review_focus: spec_compliance`, then fresh sentinel with `review_focus: code_quality`.

Update state: `uli-set-phase acceptance`

### Step 5 — Hard Acceptance Gate

**Strict. Partial acceptance does NOT advance the iteration.**

```
Agent({
  name: "prism",
  subagent_type: "claude-code-flow:prism",
  prompt: "Run acceptance for ULI iteration N. Read .claude/flow/uli/<slug>/plan-brief.md and .claude/flow/uli/<slug>/proposal.md. Run: (1) build, (2) full tests, (3) verify each CORE requirement from proposal. ACCEPT or REJECT with gap list."
})
```

**ACCEPT** (ALL must be true): build passes, tests pass, every CORE requirement verified.

On ACCEPT:
1. Write acceptance report to `.claude/flow/uli/<slug>/acceptance-report.md`
2. Update `.claude/flow/uli/product-state.md` — append completed features
4. Commit: `feat(uli-N): <iteration goal>`
5. Check loop condition:
   - If `iteration >= max_iterations` → Step 6
   - If product goal fully achieved → Step 6
   - Else → increment: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-next`; derive next iteration's slug from its expected goal and set via `uli-set-task <next-slug>`, then go to Step 1

**REJECT** (first time): route back to Step 3 with gap list (max 2 retry loops within this iteration).

**REJECT** (after 2 retries): **stop ULI, escalate to user** with gap list. Do NOT emit `<uli-done>`.

## Step 6 — Signal Completion

Apply `verification-before-completion` across all delivered features. Output:

```
## ULI Complete

**Goal:** <product goal>
**Iterations:** N/max_iterations
**Branch:** uli/...

### Delivered
- [Iteration 1] <feature> (commit: abc1234)
- [Iteration 2] <feature> (commit: def5678)

### Final verification
- Tests: X passed, 0 failed | Build: OK | Lint: clean

<uli-done>Delivered N features over M iterations: <brief summary>. All tests pass. Build OK.</uli-done>
```

`<uli-done>` must be the last thing in the message.

## ULI Golden Rules

1. **Write uli-state.json first** — Stop Hook needs it.
2. **PD runs before dev — EVERY iteration** — never start pipeline without a fresh `uli/<slug>/proposal.md`. PD MUST analyze `.claude/flow/uli/product-state.md` and produce a NEW proposal each time.
3. **One iteration = one PD proposal** — do not split, do not merge, do not skip PD.
4. **Each iteration gets its own slug-named directory** — never overwrite previous iteration artifacts.
5. **Hard acceptance** — build + tests + feature checklist ALL must pass. One failure = REJECT.
6. **REJECT after retries = escalate** — never retry more than 2 times per iteration.
7. **Never emit `<uli-done>` after a REJECT** — only on full success.
8. **Branch off main** — never commit directly to `main`/`master`.
9. **Update `.claude/flow/uli/product-state.md` after each ACCEPT** — PD needs this for next iteration.
10. **No feature creep from PD** — PD proposes, dev delivers exactly that.
11. **Ralph Loop runs tasks, not iterations** — the loop processes individual tasks within one iteration. Iteration boundary is PD→acceptance→commit.
12. **Iteration context isolation** — each iteration's agents read from files, not session history. Prior iteration outputs are invisible to new agents.
13. **VERIFY after every step** — proposal exists, plan exists, tasks done, acceptance passed. No skipping.
