---
name: Finishing Branch
version: "1.0.0"
description: "Use when implementation is complete and tests pass"
---

# Finishing Branch

## Overview

Guide completion of development work: verify tests, detect environment, present options, execute choice, clean up.

**Core principle:** Verify tests → Detect environment → Present options → Execute → Cleanup.

## Process

### Step 1: Verify Tests

Before presenting options, verify tests pass:

```bash
# Use project-appropriate test command
npm test / pytest / cargo test / python tests/run-tests.py
```

**If tests fail:** Stop. Report failures. Do not proceed to Step 2.
**If tests pass:** Continue.

### Step 2: Detect Environment

```bash
# Check if in worktree
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```

| State | Meaning |
|-------|---------|
| `GIT_DIR == GIT_COMMON` | Normal repo, no worktree cleanup needed |
| `GIT_DIR != GIT_COMMON` | In a linked worktree, cleanup may apply |

### Step 3: Present Options

**Normal repo and named-branch worktree — present exactly these 4 options:**

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Don't add explanation** — keep options concise.

### Step 4: Execute Choice

#### Option 1: Merge Locally

```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
# Verify tests on merged result
<test command>
# After merge succeeds: cleanup worktree (if applicable), then delete branch
git branch -d <feature-branch>
```

#### Option 2: Push and Create PR

```bash
git push -u origin <feature-branch>
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

**Do NOT clean up worktree** — user may need it for PR iteration.

#### Option 3: Keep As-Is

Report: "Keeping branch `<name>`. Worktree preserved at `<path>`."

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch: <name>
- Commits: <commit-list>

Type 'discard' to confirm.
```

Wait for exact confirmation. If confirmed, delete branch and cleanup worktree.

### Step 5: Cleanup Workspace

**Only for Options 1 and 4.** Options 2 and 3 preserve the workspace.

If in a worktree created by this plugin:
```bash
cd <main-repo-root>
git worktree remove <worktree-path>
git worktree prune
```

If the host environment owns the workspace — do NOT remove it.

## Quick Reference

| Option | Merge | Push | Keep Workspace | Cleanup Branch |
|--------|-------|------|----------------|----------------|
| 1. Merge locally | yes | - | - | yes |
| 2. Create PR | - | yes | yes | - |
| 3. Keep as-is | - | - | yes | - |
| 4. Discard | - | - | - | yes (force) |

## Red Flags

**Never:**
- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Remove a worktree before confirming merge success
- Clean up worktrees you didn't create
