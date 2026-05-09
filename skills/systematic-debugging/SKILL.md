---
name: Systematic Debugging
version: "2.1.0"
description: "Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes"
---

# Systematic Debugging

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

If you haven't completed Phase 1, you cannot propose fixes. Patching without understanding is how bugs multiply.

**Violating the letter of this process is violating the spirit of debugging.**

## When to Use

Use for ANY technical issue — test failures, bugs, unexpected behavior, performance problems, build failures. Especially under time pressure, when "just one quick fix" seems obvious, or after previous fixes didn't work.

## The Four Phases

Complete each phase before proceeding to the next. See `phases.md` in this directory for full details.

1. **Root Cause Investigation** — Reproduce, read errors, check changes, trace data flow
2. **Pattern Analysis** — Find working examples, compare, identify differences
3. **Hypothesis and Testing** — One hypothesis, minimal test, verify
4. **Implementation** — Failing test, single fix, verify. If >= 3 fixes failed: question architecture

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast. |
| "Emergency, no time" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern. |

## Red Flags — STOP

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- Proposing solutions before tracing data flow
- Changing multiple things in one attempt
- "One more fix attempt" (when already tried 2+)

**All of these mean: STOP. Return to Phase 1.**

## Completion Evidence

Report:
- Reproduction command or scenario
- Root cause
- Regression test added
- Verification command and result
