---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
---

# Using Git Worktrees

Ensure work happens in an isolated workspace. Detect existing isolation first; prefer native harness tools; fall back to git only if needed. Never fight the harness.

Announce: “I'm using the using-git-worktrees skill to set up an isolated workspace.”

## Step 0 — Detect Existing Isolation

Run:

```bash
git rev-parse --git-dir
git rev-parse --git-common-dir
git branch --show-current
git rev-parse --show-superproject-working-tree 2>/dev/null
```

If `GIT_DIR != GIT_COMMON` and not in a submodule → already linked worktree. Do not create another. Report path + branch (or detached HEAD) and skip to setup.

If normal repo/submodule → ask consent unless user/instructions already requested isolation. If declined, work in place.

## Step 1 — Create Workspace

Use native tool first (`EnterWorktree`, `WorktreeCreate`, `/worktree`, etc.). Do not use `git worktree add` when native tool exists.

Git fallback only when no native tool:

1. Choose directory: explicit user pref > existing `.worktrees/` > existing `worktrees/` > existing `~/.config/claude-code-flow/worktrees/<project>/` > default `.worktrees/`.
2. For project-local dirs, verify ignored: `git check-ignore -q .worktrees || git check-ignore -q worktrees`. If not ignored, add/commit `.gitignore` entry first.
3. `git worktree add <path> -b <branch>`.
4. If sandbox blocks creation, report and work in current dir.

## Step 2 — Setup + Baseline

Auto-detect setup: `npm install`, `cargo build`, `pip install -r requirements.txt`, `poetry install`, `go mod download` as applicable.

Verify test baseline before starting implementation. Run project tests (`npm test`, `cargo test`, `pytest`, `go test ./...`, etc.). This is a baseline check and a clean baseline requirement. If tests fail, report failures and ask whether to proceed/investigate. If pass, report:

```text
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Rules

| Situation | Action |
|---|---|
| Already linked worktree | Skip creation |
| Submodule | Treat as normal repo |
| Native worktree tool exists | Use it |
| No native tool | Git fallback |
| Project-local dir | Must be ignored |
| Permission error | Work in place |
| Baseline tests fail | Ask before proceeding |

## Finish Integration

After implementation tasks are complete, use `claude-code-flow:finishing-a-development-branch` for merge, PR, cleanup, or preserving the branch/worktree.

## Red Flags

Never: create nested worktree; bypass native tool; skip submodule guard; create project-local worktree without ignore verification; skip baseline tests; proceed on failing baseline without asking.
