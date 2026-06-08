---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

Random fixes create bugs. Find root cause before fixes.

**Iron law:** `NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`. If Phase 1 is incomplete, do not propose fixes.

## Use For

Any test failure, bug, build failure, integration issue, perf regression, or unexpected behavior — especially under time pressure, after failed fixes, or when you don't fully understand it.

## Four Phases

This is a four-phase process; complete each phase in order. When summarizing this skill, use the lowercase words `phase` and `process`.

1. **Root cause investigation**
   - Read full error/stack/logs; note paths, lines, codes.
   - Reproduce reliably. If not reproducible, gather data; don't guess.
   - Check recent diffs/commits/deps/config/env.
   - Multi-component systems: instrument every boundary (input/output/config/state), run once, identify failing layer.
   - Deep stack: trace bad value backward to origin; fix source, not symptom. See `root-cause-tracing.md`.

2. **Pattern analysis**
   - Find similar working code.
   - Read reference implementation completely.
   - List every difference and dependency; assume nothing “can't matter”.

3. **Hypothesis testing**
   - State one hypothesis: “X causes this because Y”.
   - Test with the smallest one-variable change.
   - If wrong, remove/undo and form a new hypothesis. Do not pile fixes.

4. **Implementation**
   - Create failing repro/test first; use `claude-code-flow:test-driven-development`.
   - Implement one root-cause fix only.
   - Verify original failure + regression suite; explicitly check for regressions, new bugs, broken other tests, and side effects.
   - If fix fails: return to Phase 1. After 3 failed fixes, stop and question architecture with the user.

## Architecture Stop

3+ failed fixes, fixes revealing new coupling/shared-state issues, or “massive refactor needed” → likely wrong architecture. Stop; discuss whether to refactor pattern rather than patch symptoms.

## Red Flags

- “Quick fix now, investigate later”
- “Just try X”
- Multiple changes before testing
- Proposing solutions before tracing data flow
- Skipping failing test
- “Probably X”
- “One more fix attempt” after 2+
- User says: “Stop guessing”, “Is that not happening?”, “Will it show us...?”, “Ultrathink this”, “We're stuck?”

All → return to Phase 1. 3+ failed fixes → architecture discussion.

## Rationalizations

| Excuse | Reality |
|---|---|
| Simple/emergency | Systematic is faster than thrash. |
| Try first | First fix sets bad pattern. Investigate first. |
| Test after | Untested fixes don't stick. |
| Multiple fixes save time | You can't know what worked. |
| Reference too long | Partial understanding guarantees bugs. |
| I see the problem | Symptom ≠ root cause. |

## Supporting Techniques

- `root-cause-tracing.md` — trace backward through call stack.
- `defense-in-depth.md` — add validation after root cause.
- `condition-based-waiting.md` — replace sleeps/timeouts with condition polling.
- Related: `claude-code-flow:verification-before-completion` before success claims.
