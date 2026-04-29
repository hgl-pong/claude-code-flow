---
name: Verification Before Completion
version: "1.0.0"
description: Use before declaring work complete, especially after implementation, bug fixes, refactors, reviews, or acceptance testing.
---

# Verification Before Completion

Never report completion from intent. Report completion from fresh evidence.

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

Keep it short:

- What changed.
- Files touched.
- Verification run.
- Residual risk or skipped checks.
