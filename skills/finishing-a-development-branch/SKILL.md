---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

# Finishing a Development Branch

Verify → detect environment → present exact options → execute choice → clean only what you own.

Announce: “I'm using the finishing-a-development-branch skill to complete this work.”

## 1. Verify Tests First

Run the full project test command. If failures: show failures and stop; no merge/PR options until green.

## 2. Detect Environment

Compare `git rev-parse --git-dir` vs `git rev-parse --git-common-dir`.

| State | Menu | Cleanup |
|---|---|---|
| Normal repo (`GIT_DIR == GIT_COMMON`) | 4 options | no worktree cleanup |
| Linked worktree, named branch | 4 options | provenance-based cleanup |
| Linked worktree, detached HEAD | 3 options, no merge | externally managed; don't remove |

Find base: `main`/`master` merge-base, or ask if unclear.

## 3. Present Exact Menu

Normal/named branch:

```text
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

Detached HEAD:

```text
Implementation complete. You're on a detached HEAD (externally managed workspace).

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)
3. Discard this work

Which option?
```

No extra explanation.

## 4. Execute Choice

1. **Merge locally:** go to main repo root; checkout base; pull; merge feature; run tests on merged result; only after success, cleanup owned worktree then delete branch.
2. **Push + PR:** push branch; create PR with summary/test plan. Do not clean worktree; user needs it for PR iteration.
3. **Keep:** report branch/path; preserve worktree.
4. **Discard:** confirm first with exact `discard`, listing branch, commits, worktree path. Then cleanup owned worktree and force-delete branch.

## 5. Cleanup Rules

Only for merge/discard. Never cleanup for PR/keep.

Owned worktrees: path under `.worktrees/`, `worktrees/`, or `~/.config/claude-code-flow/worktrees/`. For owned cleanup, go to main repo root, `git worktree remove <path>`, then `git worktree prune`, then delete branch.

Harness/external worktrees: do not remove manually. Use platform exit tool if available; otherwise leave in place.

## Red Flags

Never: proceed with failing tests; merge without testing merged result; delete without typed confirmation; force-push unless requested; remove worktree before merge success; clean harness-owned worktrees; run `git worktree remove` from inside target worktree.
