---
name: Verification Before Completion
version: "2.0.0"
description: "Use when about to claim work is complete, fixed, or passing"
---

# Verification Before Completion

## Iron Law

**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

"Tests pass" requires actual test output. "Build succeeds" requires actual build output. "Bug fixed" requires a passing regression test. Intent is not evidence. Memory is not evidence.

If you haven't run the verification command in this message, you cannot claim it passes.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Gate Function

BEFORE claiming any status:

1. **IDENTIFY** — What command proves this claim?
2. **RUN** — Execute the FULL command (fresh, complete)
3. **READ** — Full output, check exit code, count failures
4. **VERIFY** — Does output confirm the claim? If NO: state actual status. If YES: claim WITH evidence.
5. **ONLY THEN** — Make the claim.

Skip any step = not verifying.

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Requirements met | Line-by-line checklist | Tests passing |

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter is not compiler |
| "Agent said success" | Verify independently |
| "I just ran tests a minute ago" | A minute ago is not now. Re-run. |
| "It's a trivial change" | Trivial changes break things constantly. |
| "The code looks correct" | Looking correct and being correct are different. |
| "I'll verify after this next change" | Verify now or don't claim done. |

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!")
- About to commit/push/PR without verification
- Trusting agent success reports
- "I'm pretty sure this works"
- "The tests should pass"
- "It worked in my head"

## Process

Before saying work is done:

1. Confirm the requested behavior or deliverable exists.
2. Run the narrowest relevant test or command.
3. Run broader checks when the change has broader impact.
4. Check `.claude/flow/verification-evidence.jsonl` for latest recorded evidence when hooks are enabled.
5. Check `git status --short` and list files changed.
6. Note any checks you could not run and why.

## Evidence Standards

| Claim | Evidence |
|---|---|
| Tests pass | Exact command run and pass/fail summary |
| Build succeeds | Exact build command and result |
| Bug fixed | Regression test or reproduction now passes |
| UI works | Screenshot/browser check or explicit render verification |
| Review passed | Review result and files reviewed |

## Final Report

Short. 3-5 bullets or 1-2 short paragraphs. Do not recap the whole workflow.

- What changed
- Files touched
- Verification run
- Residual risk or skipped checks
