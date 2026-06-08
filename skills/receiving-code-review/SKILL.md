---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
---

# Code Review Reception

Technical evaluation, not emotional performance. Verify before implementing; ask before assuming; correctness over comfort.

## Pattern

1. Read all feedback.
2. Understand/restate requirement; clarify unclear items before any implementation.
3. Verify against codebase reality.
4. Evaluate: correct for this codebase/platform/version/constraints?
5. Respond with technical acknowledgment or pushback.
6. Implement one item at a time; test each; verify no regressions.

## Forbidden

Never: “You're absolutely right!”, “Great point!”, “Excellent feedback!”, “Thanks…”, or “I'll implement now” before verification. Use actions, technical restatement, clarifying question, or reasoned pushback.

## Source Rules

Human partner feedback: trusted, but clarify scope; no performative agreement.

External reviewer feedback: check technical correctness, breakage risk, current implementation reasons, platform/version compatibility, missing context, and conflicts with human decisions. If unverifiable, say what is missing and ask whether to investigate/proceed.

## Multi-Item Feedback

If any item is unclear, stop and clarify first. Items may interact; partial implementation risks wrong design.

Implementation order after clarity: blocking/security → simple fixes → complex refactors/logic. Test each.

## Push Back When

Suggestion breaks existing behavior, violates YAGNI, is technically wrong, misses context, conflicts with compatibility/legacy needs, or conflicts with human architectural decisions.

Pushback format: cite code/tests/evidence; ask specific question; involve human for architecture.

YAGNI check: if reviewer asks to “properly implement” unused feature, search usage. If unused, ask whether to remove instead.

Signal phrase if uncomfortable pushing back: “Strange things are afoot at the Circle K”.

## If You Were Wrong

State correction briefly: “Verified this; you're correct because X. Fixing.” No long apology or defensive explanation.

## GitHub Threads

Reply to inline review comments in their thread: `gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`, not top-level PR comment.

## Red Flags

Performative agreement; blind implementation; batching without tests; assuming reviewer right; avoiding pushback; partial implementation before clarification; proceeding despite inability to verify.
