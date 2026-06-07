#!/usr/bin/env bash
# E2E: Using Git Worktrees Skill
# Verifies the git worktrees skill provides correct instructions and behavioral rules.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Git Worktrees Skill"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and purpose..."
output=$(run_claude "What is the claude-code-flow:using-git-worktrees skill? What is its purpose?" 120)

assert_contains "$output" "git.*worktree\|Git.*Worktree\|worktree" \
    "Skill is recognized by name" || true
assert_contains "$output" "isolate\|branch\|workspace\|parallel" \
    "Skill purpose includes isolation/workspace" || true

echo ""

# ── Test 2: Worktree creation process ──
echo "Test 2: Worktree creation..."
output=$(run_claude "According to the using-git-worktrees skill, how should you create an isolated workspace? What are the key steps?" 120)

assert_contains "$output" "EnterWorktree\|enter.*worktree\|create.*worktree" \
    "Mentions EnterWorktree tool" || true
assert_contains "$output" "branch\|checkout\|base.*branch\|isolate" \
    "Mentions branch/checkout" || true

echo ""

# ── Test 3: Start from clean baseline ──
echo "Test 3: Clean baseline requirement..."
output=$(run_claude "In the using-git-worktrees skill, should you verify the baseline before starting work? What should be checked?" 120)

assert_contains "$output" "test.*baseline\|verify.*test\|baseline.*check\|clean.*baseline" \
    "Mentions verifying test baseline" || true

echo ""

# ── Test 4: Main branch safety ──
echo "Test 4: Main branch protection..."
output=$(run_claude "In the using-git-worktrees skill, can you implement features directly on the main or master branch?" 120)

assert_contains "$output" "no\|never\|should.*not\|don.*main\|don.*master\|must.*not" \
    "Says never implement on main/master" || true
assert_contains "$output" "worktree\|branch\|isolate\|separate" \
    "Directs to use worktree/branch instead" || true

echo ""

# ── Test 5: Finishing integration ──
echo "Test 5: Finishing integration..."
output=$(run_claude "According to the using-git-worktrees skill, what happens after all tasks are complete? What skill should be used?" 120)

assert_contains "$output" "finishing\|merge\|cleanup\|finishing-a-development-branch" \
    "Mentions finishing skill or merge/cleanup" || true

echo ""

report_failures
