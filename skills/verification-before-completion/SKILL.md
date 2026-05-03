---
name: Verification Before Completion
version: "1.0.0"
description: Use before declaring work complete, especially after implementation, bug fixes, refactors, reviews, or acceptance testing.
---

# Verification Before Completion

## IRON LAW

**NEVER CLAIM COMPLETION WITHOUT FRESH VERIFICATION EVIDENCE.**

"Tests pass" requires actual test output. "Build succeeds" requires actual build output. "Bug fixed" requires a passing regression test. Intent is not evidence. Memory is not evidence.

### Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I just ran tests a minute ago" | A minute ago is not now. Re-run. |
| "It's a trivial change, can't break anything" | Trivial changes break things constantly. Run the suite. |
| "The code looks correct" | Looking correct and being correct are different. Execute it. |
| "I'll verify after this next change" | There is no "next change" — verify now or don't claim done. |
| "Build passed in CI" | CI is not your machine. Verify locally before claiming done. |

### Red Flags — STOP if you catch yourself thinking:

- "I'm pretty sure this works"
- "The tests should pass"
- "It worked in my head"
- "I don't need to check, I've done this before"
- "Verification is someone else's job"

## Process

Before saying work is done:

1. Confirm the requested behavior or deliverable exists.
2. Run the narrowest relevant test or command.
3. Run broader checks when the change has broader impact.
4. Check `.claude/flow/verification-evidence.jsonl` for the latest recorded test/build/lint evidence when hooks are enabled.
5. Check `git status --short` and list the files you changed.
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

Keep it short. Default to 3-5 bullets or 1-2 short paragraphs. Do not recap the whole workflow unless the user asks.

- What changed.
- Files touched.
- Verification run.
- Residual risk or skipped checks.
