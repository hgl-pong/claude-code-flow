#!/usr/bin/env bash
# E2E: Finishing a Development Branch Skill
# Verifies the finishing skill provides correct merge/cleanup options.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Finishing a Development Branch"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and purpose..."
output=$(run_claude "What is the claude-code-flow:finishing-a-development-branch skill? What does it do?" 120)

assert_contains "$output" "finishing\|Finishing.*Branch\|finishing-a-development-branch" \
    "Skill is recognized by name" || true
assert_contains "$output" "merge\|PR\|pull request\|cleanup\|branch" \
    "Skill purpose includes merge/PR/cleanup" || true

echo ""

# ── Test 2: Four options ──
echo "Test 2: Completion options..."
output=$(run_claude "In the finishing-a-development-branch skill, what are the options presented at the end of a branch?" 120)

assert_contains "$output" "merge\|[Mm]erge.*back\|merge.*base" \
    "Mentions merge back to base branch (Option 1)" || true

echo ""

# ── Test 3: Verification before finish ──
echo "Test 3: Pre-finish verification..."
output=$(run_claude "In the finishing-a-development-branch skill, what should be verified before finishing?" 120)

assert_contains "$output" "test\|verify\|check\|review" \
    "Mentions verification before finishing" || true

echo ""

# ── Test 4: Worktree cleanup ──
echo "Test 4: Worktree cleanup..."
output=$(run_claude "In the finishing-a-development-branch skill, what happens to the worktree after finishing?" 120)

assert_contains "$output" "worktree\|cleanup\|remove\|clean.*up\|delete" \
    "Mentions worktree cleanup" || true

echo ""

report_failures
