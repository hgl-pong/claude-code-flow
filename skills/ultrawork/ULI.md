# ULI — Ultra Loop Iteration Branch

> Enter this branch when activation context contains `ULI MODE ACTIVE`.

ULI is a continuous product iteration loop. Each iteration: **PD proposes → workflow-plan → dev pipeline executes → hard acceptance validates → next iteration**.

## Iteration Document Structure

Each iteration stores artifacts in a dedicated directory:

```
.claude/flow/uli/iterations/
├── 1/
│   ├── proposal.md          # PD requirements proposal
│   ├── plan.md              # Oracle implementation plan
│   └── acceptance-report.md # Acceptance verdict + evidence
├── 2/
│   └── ...
└── ...
```

Working copies at fixed paths (for agents that reference them):
- `.claude/flow/uli-proposal.md` — current iteration's proposal
- `.claude/flow/uli-acceptance-report.md` — last iteration's acceptance report
- `.claude/plans/plan-brief.md` — current iteration's task brief

## ULI Stop Hook

`uli-stop-hook.sh` blocks exit until `<uli-done>` is emitted. Same "Ralph Wiggum technique" as ULW — the hook enforces completion.

## Step 0 — Initialize

1. Write ULI state file via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-init "<GOAL_FROM_USER_PROMPT>"` (default: max_iterations=10)
2. Set mode: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode autonomous`
3. Set phase: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan`
4. Create/verify `.claude/flow/product-state.md` (goal + completed features + known gaps).
5. Create iteration directory: `mkdir -p .claude/flow/uli/iterations/1`
6. Branch off main: `git checkout -b uli/$(date +%Y%m%d-%H%M%S)-iteration-loop`

## Step 1 — Start Iteration (repeat for each iteration)

Get current iteration number `N` from `uli-state.json` (or `flow-state.py uli-get`).

Create iteration directory: `mkdir -p .claude/flow/uli/iterations/<N>`

**Context isolation**: this iteration's agents should NOT depend on session history from prior iterations. All necessary context flows through files: `product-state.md` (completed features + gaps), `uli-acceptance-report.md` (last verdict), and the current iteration's `proposal.md`. Do not summarize or reference prior iteration agent outputs in prompts.

Update state: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-set-phase pd_generating`

## Step 2 — PD Agent

```
Agent({
  name: "pd",
  subagent_type: "claude-code-flow:pd",
  model: "sonnet",
  prompt: """
## Envelope
- **Goal:** <product goal>
- **Your Task:** Propose requirements for iteration N of this product.
- **Iteration:** N / max_iterations
- **Completed Features:** <read from product-state.md>
- **Last Verdict:** <read from uli-acceptance-report.md, may not exist>
- **Constraints:** Max 3 CORE, every CORE must have executable acceptance criterion.

See agents/pd.md for full format. Output to .claude/flow/uli/iterations/<N>/proposal.md and copy to .claude/flow/uli-proposal.md.
"""
})
```

Wait for PD. Read `uli-proposal.md` (working copy). Verify at least 1 CORE requirement with concrete acceptance criterion. If none or untestable, stop ULI and report to user.

Update state: `uli-set-phase dev_pipeline`

## Step 3 — Workflow-Plan & Dev Pipeline

Run the full workflow-plan pipeline in autonomous mode (all approval gates auto-pass). Use PD proposal as input spec.

### 3a. Planning Phase

**Research** (scout, if needed) — trigger when: external API/library integration needed, unfamiliar domain, or cross-module dependencies. Skip for pure internal logic.

**Design** (atlas, if needed) — trigger when: new system/component, significant architectural change, or 3+ modules affected. Skip for incremental changes within existing structure.

**Plan** (oracle, always) — decompose CORE requirements into phased tasks:
1. Oracle reads `.claude/flow/uli-proposal.md`
2. Creates tasks via `TaskCreate` with `blockedBy` dependencies
3. Writes implementation plan to `.claude/flow/uli/iterations/<N>/plan.md`
4. Writes agent brief to `.claude/plans/plan-brief.md` (working copy for downstream agents)

Do NOT show plan to user (autonomous mode).

### 3b. Implementation (Ralph Loop + Parallel Scheduler)

**Ralph Loop**: each agent dispatch is stateless — self-contained prompt via Context Envelope, no prior agent output carried forward. PICK → ENVELOPE → DISPATCH → WAIT → VERIFY → RECORD → LOOP.

Use parallel scheduler (see dev-orchestrator Step 5): file conflict analysis, worktree isolation for conflicting tasks, dispatch non-conflicting agents in a single message with `run_in_background: true`. Max 3 parallel for forge/weaver, 2 for prism, 1 for anvil. Every agent prompt must use the **Context Envelope** format.

Test-first RED→GREEN→refactor→record evidence. Frontend→weaver; backend→forge; tests→prism; build→anvil.

### 3c. Sentinel Review (auto, two-stage)

**Stage 1: Spec Compliance** — does implementation match the iteration plan? Check every CORE requirement.
**Stage 2: Code Quality** — only runs if Stage 1 passes. Check naming, structure, error handling, test coverage.

APPROVE→acceptance; REQUEST CHANGES→back to implementer (max 2 loops); still failing→skip to Step 4 with `acceptance_status = "sentinel_failed"`.

Update state: `uli-set-phase acceptance`

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
1. Write acceptance report to `.claude/flow/uli/iterations/<N>/acceptance-report.md`
2. Copy to `.claude/flow/uli-acceptance-report.md` (working copy)
3. Update `product-state.md` — append completed features
4. Commit: `feat(uli-N): <iteration goal>`
5. Go to Step 5

**REJECT** (first time): route back to implementer with gap list (max 2 retry loops).

**REJECT** (after 2 retries): **stop ULI, escalate to user** with gap list. Do NOT emit `<uli-done>`.

## Step 5 — Check Loop Condition

```
if iteration >= max_iterations → proceed to Step 6
else → increment iteration (uli-next), go to Step 1
```

Increment via: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py uli-next`

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
3. **Each iteration gets its own directory** — never overwrite previous iteration artifacts.
4. **Hard acceptance** — build + tests + feature checklist ALL must pass. One failure = REJECT.
5. **REJECT after retries = escalate** — never retry more than 2 times per iteration.
6. **Never emit `<uli-done>` after a REJECT** — only on full success.
7. **Branch off main** — never commit directly to `main`/`master`.
8. **Update product-state.md after each ACCEPT** — PD needs this for next iteration.
9. **No feature creep from PD** — PD proposes, dev delivers exactly that.
10. **Workflow-plan every iteration** — each iteration goes through research/design/plan as needed before implementation.
11. **Ralph Loop: stateless dispatch** — every agent prompt is self-contained. Never carry prior agent output into the next dispatch.
12. **Iteration context isolation** — each iteration's agents read from files, not session history. Prior iteration outputs are invisible to new agents.
