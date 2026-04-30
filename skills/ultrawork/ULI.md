# ULI — Ultra Loop Iteration Branch

> Enter this branch when activation context contains `ULI MODE ACTIVE`.

ULI is a continuous product iteration loop. Each iteration: **PD proposes → dev pipeline executes → hard acceptance validates → next iteration**.

## ULI Stop Hook

`uli-stop-hook.sh` blocks exit until `<uli-done>` is emitted. Same "Ralph Wiggum technique" as ULW — the hook enforces completion.

## Step 0 — Initialize

1. Write ULI state file via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-init "<GOAL_FROM_USER_PROMPT>"` (default: max_iterations=10)
2. Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous`
3. Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan`
4. Create/verify `.claude/flow/product-state.md` (goal + completed features + known gaps).
5. Branch off main: `git checkout -b uli/$(date +%Y%m%d-%H%M%S)-iteration-loop`

## Step 1 — Start Iteration (repeat for each iteration)

Update state: `current_phase = "pd_generating"`, `pd_proposal_ready = false`, `acceptance_status = null`.

## Step 2 — PD Agent

```
Agent({
  name: "pd",
  subagent_type: "claude-code-flow:pd",
  model: "sonnet",
  prompt: "Generate requirements for ULI iteration N. Goal: <goal>. Read .claude/flow/product-state.md and .claude/flow/uli-acceptance-report.md (if exists). Output to .claude/flow/uli-proposal.md. See agents/pd.md for format."
})
```

Wait for PD. Read `uli-proposal.md`. Verify at least 1 CORE requirement with concrete acceptance criterion. If none or untestable, stop ULI and report to user.

Update state: `pd_proposal_ready = true`, `current_phase = "dev_pipeline"`

## Step 3 — Dev Pipeline

Same as dev-orchestrator autonomous mode with PD proposal as input spec:

1. **oracle** (auto) — decompose CORE requirements into tasks via TaskCreate. Write agent brief to `plan-brief.md`. Do NOT show plan.
2. **Implementation** (DAG-aware, max 2 parallel) — test-first RED→GREEN→refactor→record evidence. Frontend→weaver; backend→forge; tests→prism; build→anvil.
3. **Sentinel review** (auto) — APPROVE→acceptance; REQUEST CHANGES→back to implementer (max 2 loops); still failing→skip to Step 4 with `acceptance_status = "sentinel_failed"`.

Update state: `current_phase = "acceptance"`

## Step 4 — Hard Acceptance Gate

**Strict. Partial acceptance does NOT advance the iteration.**

```
Agent({
  name: "validator",
  subagent_type: "claude-code-flow:validator",
  prompt: "Run acceptance for ULI iteration N. Read .claude/plans/plan-brief.md. Run: (1) build, (2) full tests, (3) verify each CORE requirement from uli-proposal.md. ACCEPT or REJECT with gap list."
})
```

**ACCEPT** (ALL must be true): build passes, tests pass, every CORE requirement verified.

On ACCEPT:
1. Write `uli-acceptance-report.md` with verdict + verified requirements + test results + commits
2. Update `product-state.md` — append completed features
3. Commit: `feat(uli-N): <iteration goal>`
4. Update state: `iteration++`, `acceptance_status = "accepted"`
5. Go to Step 5

**REJECT** (first time): route back to implementer with gap list (max 2 retry loops).

**REJECT** (after 2 retries): **stop ULI, escalate to user** with gap list. Do NOT emit `<uli-done>`.

## Step 5 — Check Loop Condition

```
if iteration >= max_iterations → proceed to Step 6
else → increment iteration, go to Step 1
```

Optionally: if product goal is fully achieved before max_iterations, emit `<uli-done>` early.

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
2. **PD runs before dev** — never start pipeline without `uli-proposal.md`.
3. **Hard acceptance** — build + tests + feature checklist ALL must pass. One failure = REJECT.
4. **REJECT after retries = escalate** — never retry more than 2 times per iteration.
5. **Never emit `<uli-done>` after a REJECT** — only on full success.
6. **Branch off main** — never commit directly to `main`/`master`.
7. **Update product-state.md after each ACCEPT** — PD needs this for next iteration.
8. **No feature creep from PD** — PD proposes, dev delivers exactly that.
