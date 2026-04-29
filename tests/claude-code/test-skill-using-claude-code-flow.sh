#!/usr/bin/env bash
# E2E test: using-claude-code-flow skill
# Verifies Claude understands the entry-point skill and the gate philosophy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: using-claude-code-flow skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill is recognizable and describes skill-selection-first
# ------------------------------------------------------------------
echo "Test 1: Skill selection before action..."
output="$(run_claude \
  "What does the using-claude-code-flow skill tell you to do before taking any action?" \
  "$timeout_seconds")"
assert_contains "$output" "skill|select.*skill|load.*skill|check.*skill" "Emphasises skill selection"
assert_contains "$output" "using-claude-code-flow" "Skill name appears in output"
echo ""

# ------------------------------------------------------------------
# Test 2: Lists the companion skills in order
# ------------------------------------------------------------------
echo "Test 2: Companion skills listed..."
output="$(run_claude \
  "List all the companion skills mentioned in using-claude-code-flow. What is each one for?" \
  "$timeout_seconds")"
assert_contains "$output" "brainstorm" "mentions brainstorming skill"
assert_contains "$output" "writing-plans|write.*plan" "mentions writing-plans skill"
assert_contains "$output" "testing-strategy|TDD|test.*first" "mentions testing-strategy skill"
assert_contains "$output" "systematic-debugging|debugging" "mentions systematic-debugging skill"
assert_contains "$output" "verification-before-completion|verification" "mentions verification skill"
echo ""

# ------------------------------------------------------------------
# Test 3: Gate philosophy — design approval before broad implementation
# ------------------------------------------------------------------
echo "Test 3: Design gate before implementation..."
output="$(run_claude \
  "According to using-claude-code-flow, when must you get design approval? What happens if you skip it?" \
  "$timeout_seconds")"
assert_contains "$output" "brainstorm|design.*approval|approved" "Mentions design gate"
assert_contains "$output" "before.*implement|prior.*implement|implement.*after" "Gate comes before implementation"
echo ""

# ------------------------------------------------------------------
# Test 4: Workflow order
# ------------------------------------------------------------------
echo "Test 4: High-level workflow order..."
output="$(run_claude \
  "Describe the full workflow order in using-claude-code-flow from receiving a task to closing it." \
  "$timeout_seconds")"
assert_order "$output" "brainstorm|design" "plan|write.*plan" "brainstorm before plan"
assert_order "$output" "plan|write.*plan" "implement|execute" "plan before implementation"
assert_order "$output" "implement|execute" "verification|verify" "implementation before verification"
echo ""

echo "=== All using-claude-code-flow tests passed ==="
