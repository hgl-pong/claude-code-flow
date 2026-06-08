---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
---

# Verification Before Completion

Evidence before claims. Completion claims without fresh verification are dishonest.

**Iron law:** `NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`.

If you didn't run the verification command in this message, you cannot claim it passes.

## Gate

Before any success/completion/correctness claim:

1. Identify command/evidence proving it.
2. Run full fresh command.
3. Read output + exit code + failure count.
4. If evidence fails, report actual state.
5. Only if evidence confirms, state claim with evidence.

Skip any step = lying, not verifying.

## Claim → Required Evidence

| Claim | Requires | Not enough |
|---|---|---|
| Tests pass | test output, 0 failures | previous run |
| Build succeeds | build command exit 0 | lint passing |
| Bug fixed | original symptom/repro passes | code changed |
| Regression test works | red-green verified | pass once |
| Agent completed | diff + independent verification | agent report |
| Requirements met | checklist against plan/spec | tests only |

## Red Flags

“Should/probably/seems”; satisfaction words before evidence; commit/push/PR before verification; trusting agents; partial checks; tired “just this once”; any wording implying success before running proof.

## Patterns

- Tests: run command → see pass count → then say tests pass.
- Regression: write/run pass → revert fix/run must fail → restore/run pass.
- Requirements: re-read plan/spec → checklist each item → report gaps or verified items.
- Delegation: agent report → inspect diff → run verification → report actual state.

## Rationalizations

| Excuse | Reality |
|---|---|
| Should work | Run it. |
| Confident | Evidence beats confidence. |
| Linter passed | Lint ≠ build/tests. |
| Agent said success | Verify independently. |
| Partial enough | Partial proves little. |

Rule applies to exact phrases, paraphrases, implications, and positive statements about work state. Run command, read output, then claim.
