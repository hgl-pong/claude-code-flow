#!/usr/bin/env bash
# E2E test: dev-orchestrator skill
# Verifies Claude understands the agent roster, mode selection, and pipeline gates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: dev-orchestrator skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill recognized and pipeline stages described
# ------------------------------------------------------------------
echo "Test 1: Pipeline stages described..."
output="$(run_claude \
  "What is the dev-orchestrator skill? Describe the main pipeline stages." \
  "$timeout_seconds")"
assert_contains "$output" "dev.orchestrator|orchestrat" "skill name present"
assert_contains "$output" "brainstorm|design|plan|implement|review|accept" "Pipeline stages mentioned"
echo ""

# ------------------------------------------------------------------
# Test 2: Mode selection (quick / standard / full)
# ------------------------------------------------------------------
echo "Test 2: Mode selection described..."
output="$(run_claude \
  "What modes does the dev-orchestrator skill support and when should each be used?" \
  "$timeout_seconds")"
assert_contains "$output" "quick" "mentions quick mode"
assert_contains "$output" "standard" "mentions standard mode"
assert_contains "$output" "full|comprehensive" "mentions full mode"
echo ""

# ------------------------------------------------------------------
# Test 3: Agent roster — named agents
# ------------------------------------------------------------------
echo "Test 3: Named agents in roster..."
output="$(run_claude \
  "List the named agents in the dev-orchestrator skill and their roles." \
  "$timeout_seconds")"
assert_contains "$output" "forge|weaver|sentinel|validator|oracle|atlas|prism|anvil|chronicler" \
  "Named agents appear"
echo ""

# ------------------------------------------------------------------
# Test 4: Review gate before commit
# ------------------------------------------------------------------
echo "Test 4: Review gate before commit..."
output="$(run_claude \
  "In dev-orchestrator, which agent performs code review and when does it happen?" \
  "$timeout_seconds")"
assert_contains "$output" "sentinel|review" "sentinel/review agent mentioned"
assert_contains "$output" "before.*commit|pre.*commit|commit.*after" "Review happens before commit"
echo ""

# ------------------------------------------------------------------
# Test 5: Acceptance gate
# ------------------------------------------------------------------
echo "Test 5: Acceptance testing gate..."
output="$(run_claude \
  "What is the acceptance gate in dev-orchestrator? Which agent handles it?" \
  "$timeout_seconds")"
assert_contains "$output" "validator|acceptance" "validator/acceptance mentioned"
assert_contains "$output" "functional|behav|end.to.end|E2E|integrat" "Describes acceptance testing"
echo ""

echo "=== All dev-orchestrator skill tests passed ==="
