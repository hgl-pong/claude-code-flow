#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-240}"

prompt='You are in a repository containing the claude-code-flow Claude Code plugin. Explain what /brainstorm, /write-plan, /execute-plan, /workflow-plan, /quick-fix, and /workflow-status are for. Include the expected order for a non-trivial feature.'

output="$(run_claude "$prompt" "$timeout_seconds")"

assert_contains "$output" "/brainstorm" "mentions brainstorm command"
assert_contains "$output" "/write-plan" "mentions write-plan command"
assert_contains "$output" "/execute-plan" "mentions execute-plan command"
assert_contains "$output" "/workflow-plan" "mentions workflow-plan command"
assert_contains "$output" "/quick-fix" "mentions quick-fix command"
assert_contains "$output" "/workflow-status" "mentions workflow-status command"
assert_order "$output" "brainstorm" "write-plan" "brainstorm before write-plan"
assert_order "$output" "write-plan" "execute-plan" "write-plan before execute-plan"
