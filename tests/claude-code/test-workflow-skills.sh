#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-240}"

prompt='You are in a repository containing the claude-code-flow Claude Code plugin. Briefly describe the workflow discipline taught by these skills: dev-orchestrator, brainstorming, planning, testing-strategy, and systematic-debugging. Keep the answer under 12 bullets.'

output="$(run_claude "$prompt" "$timeout_seconds")"

assert_contains "$output" "dev-orchestrator|skill selection|entry routing|pipeline coordination" "mentions dev-orchestrator/routing"
assert_contains "$output" "brainstorm|design.*approval|approved design" "mentions brainstorming/design gate"
assert_contains "$output" "planning|implementation plan|test-first.*plan" "mentions planning"
assert_contains "$output" "testing-strategy|TDD|failing test|RED" "mentions TDD"
assert_contains "$output" "systematic-debugging|reproduce|root cause" "mentions systematic debugging"

output="$(run_claude "I have a multi-step implementation that needs coordination and planning." "$timeout_seconds")"
assert_contains "$output" "plan|dev-orchestrator" "plugin planning gets selected"
assert_contains "$output" "brainstorm|planning|dev-orchestrator" "planning path includes the right companion skills"

output="$(run_claude "I think this should probably enter plan mode." "$timeout_seconds")"
assert_contains "$output" "use /plan|avoid invoking EnterPlanMode|plugin plan" "plan mode phrasing is redirected to plugin planning"

output="$(run_claude "I am changing UI behavior and backend state together." "$timeout_seconds")"
assert_contains "$output" "brainstorm|planning|dev-orchestrator" "cross-domain work is routed to planning and orchestration"
