#!/usr/bin/env bash
# Test: Worktree native preference
# Claude 2.1+ natively knows EnterWorktree. Verifies agent uses native tool
# (not raw git worktree add) for workspace isolation.
#
# Updated for Claude 2.1: all phases expect EnterWorktree or equivalent native tool.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

RUNS="${1:-1}"

SCENARIO='IMPORTANT: This is a real task. Choose and act.

You need to implement a small feature (add a "version" field to package.json).
This should be done in an isolated workspace to protect the main branch.

You have the using-git-worktrees skill available. Set up the isolated workspace now.
Do NOT actually implement the feature — just set up the workspace and report what you did.

Respond with EXACTLY what tool/command you used to create the workspace.'

echo "=== Worktree Native Preference Test ==="
echo ""

pass=0
fail=0

for i in $(seq 1 "$RUNS"); do
    test_dir=$(create_test_project)
    cd "$test_dir"
    git init -q && git commit -q --allow-empty -m "init"

    output=$(run_claude "$SCENARIO" 120)

    if [ "$RUNS" -eq 1 ]; then
        echo "Agent output:"
        echo "$output"
        echo ""
    fi

    used_git_worktree_add=$(echo "$output" | grep -qi "git worktree add" && echo "yes" || echo "no")

    # Claude 2.1+ should use EnterWorktree or equivalent native tool, never raw git worktree add
    if [ "$used_git_worktree_add" = "no" ]; then
        pass=$((pass + 1))
        [ "$RUNS" -gt 1 ] && echo "  Run $i: PASS (no git worktree add)"
    else
        fail=$((fail + 1))
        [ "$RUNS" -gt 1 ] && echo "  Run $i: FAIL (used git worktree add)"
        [ "$RUNS" -gt 1 ] && echo "    Output: ${output:0:200}"
    fi

    cleanup_test_project "$test_dir"
done

echo ""
echo "--- Results: $pass/$RUNS passed, $fail/$RUNS failed ---"

if [ "$fail" -gt 0 ]; then
    echo "[FAIL] Agent used raw git worktree add"
    exit 1
else
    echo "[PASS] Agent used native worktree tool"
    exit 0
fi
