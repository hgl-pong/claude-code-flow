#!/usr/bin/env bash
# E2E test: testing-strategy skill
# Verifies Claude understands RED-GREEN-REFACTOR, test pyramid, and no-mock-by-default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: testing-strategy skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill recognized and TDD cycle described
# ------------------------------------------------------------------
echo "Test 1: TDD cycle (RED-GREEN-REFACTOR)..."
output="$(run_claude \
  "Describe the TDD cycle as defined in the testing-strategy skill." \
  "$timeout_seconds")"
assert_contains "$output" "RED|red|failing" "mentions RED phase"
assert_contains "$output" "GREEN|green|pass" "mentions GREEN phase"
assert_contains "$output" "REFACTOR|refactor|clean" "mentions REFACTOR phase"
assert_order "$output" "RED|red|failing" "GREEN|green|pass" "RED before GREEN"
assert_order "$output" "GREEN|green|pass" "REFACTOR|refactor|clean" "GREEN before REFACTOR"
echo ""

# ------------------------------------------------------------------
# Test 2: Failing test first
# ------------------------------------------------------------------
echo "Test 2: Failing test required before implementation..."
output="$(run_claude \
  "In testing-strategy, can you write the implementation before you have a failing test?" \
  "$timeout_seconds")"
assert_contains "$output" "no|must.*fail|failing.*test.*first|test.*before.*impl" \
  "Failing test required first"
echo ""

# ------------------------------------------------------------------
# Test 3: Test pyramid
# ------------------------------------------------------------------
echo "Test 3: Test pyramid layers..."
output="$(run_claude \
  "What is the test pyramid in the testing-strategy skill? Name the layers from bottom to top." \
  "$timeout_seconds")"
assert_contains "$output" "unit" "mentions unit tests"
assert_contains "$output" "integration" "mentions integration tests"
assert_contains "$output" "e2e|end.to.end|acceptance|system" "mentions top layer"
assert_order "$output" "unit" "integration" "unit below integration"
echo ""

# ------------------------------------------------------------------
# Test 4: Mocking guidance
# ------------------------------------------------------------------
echo "Test 4: Mocking philosophy..."
output="$(run_claude \
  "What is the testing-strategy skill's stance on mocking? When is it acceptable?" \
  "$timeout_seconds")"
assert_contains "$output" "avoid|sparingly|minimal|last resort|real|prefer.*real" \
  "Cautions against over-mocking"
echo ""

# ------------------------------------------------------------------
# Test 5: Test naming convention
# ------------------------------------------------------------------
echo "Test 5: Test names describe behaviour..."
output="$(run_claude \
  "How should tests be named according to testing-strategy? Give the guiding principle." \
  "$timeout_seconds")"
assert_contains "$output" "behav|should|given|when|describe|intent|readable" \
  "Test names describe behaviour"
echo ""

echo "=== All testing-strategy skill tests passed ==="
