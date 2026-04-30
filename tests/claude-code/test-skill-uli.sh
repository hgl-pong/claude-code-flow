#!/usr/bin/env bash
# E2E test: ULI mode — knowledge and comprehension
#
# Verifies Claude understands:
#   - What ULI mode is and how to activate it
#   - The PD agent's role and output format
#   - The hard acceptance gate requirement
#   - How ULI differs from ULW
#   - The iteration loop structure
#
# Fast test — no real implementation, ~2-5 min.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-240}"

echo "=== Test: ULI mode skill and command ==="
echo ""

# ------------------------------------------------------------------
# Test 1: ULI mode described — activation and basic concept
# ------------------------------------------------------------------
echo "Test 1: ULI mode activation and concept..."
output="$(run_claude \
  "What is ULI mode in claude-code-flow? How do you activate it and what happens?" \
  "$timeout_seconds")"
assert_contains "$output" "uli" "ULI keyword mentioned"
assert_contains "$output" "iter|loop|cycle" "Iteration/loop concept present"
assert_contains "$output" "PD|product.*manager|product.*agent" "PD agent mentioned"
echo ""

# ------------------------------------------------------------------
# Test 2: PD agent role
# ------------------------------------------------------------------
echo "Test 2: PD agent role and output..."
output="$(run_claude \
  "In ULI mode, what does the PD agent do and what does it output?" \
  "$timeout_seconds")"
assert_contains "$output" "PD|product.*manager" "PD agent mentioned"
assert_contains "$output" "proposal|requirement|uli-proposal" "Proposal/requirements mentioned"
assert_contains "$output" "CORE|acceptance.*criter" "CORE requirements or acceptance criteria"
echo ""

# ------------------------------------------------------------------
# Test 3: Hard acceptance gate
# ------------------------------------------------------------------
echo "Test 3: Hard acceptance gate requirements..."
output="$(run_claude \
  "What is the hard acceptance gate in ULI mode? What must pass before the next iteration starts?" \
  "$timeout_seconds")"
assert_contains "$output" "build|compile" "Build check mentioned"
assert_contains "$output" "test" "Tests mentioned"
assert_contains "$output" "all.*pass|pass.*all|hard|strict" "Strictness of the gate"
echo ""

# ------------------------------------------------------------------
# Test 4: ULI vs ULW distinction
# ------------------------------------------------------------------
echo "Test 4: ULI vs ULW distinction..."
output="$(run_claude \
  "What is the difference between ULI and ULW in claude-code-flow?" \
  "$timeout_seconds")"
assert_contains "$output" "ulw|ultrawork" "ULW mentioned"
assert_contains "$output" "uli" "ULI mentioned"
assert_contains "$output" "single.*task|one.*task|task.*once|loop|multiple.*iter" \
  "Explains single-task vs loop distinction"
echo ""

# ------------------------------------------------------------------
# Test 5: Iteration loop structure
# ------------------------------------------------------------------
echo "Test 5: Iteration loop structure..."
output="$(run_claude \
  "Describe the iteration loop in ULI mode step by step." \
  "$timeout_seconds")"
assert_order "$output" "PD|product" "implement|dev|build" "PD runs before dev pipeline"
assert_contains "$output" "accept|validat|verif" "Acceptance/validation step present"
assert_contains "$output" "<uli-done>|uli.done" "Completion signal mentioned"
echo ""

# ------------------------------------------------------------------
# Test 6: Rejection handling
# ------------------------------------------------------------------
echo "Test 6: Rejection handling and retry limit..."
output="$(run_claude \
  "In ULI mode, what happens when the acceptance gate rejects an iteration? How many retries are allowed?" \
  "$timeout_seconds")"
assert_contains "$output" "reject|fail|REJECT" "Rejection scenario covered"
assert_contains "$output" "retry|re.try|attempt" "Retry mechanism mentioned"
assert_contains "$output" "2|two|max" "Retry limit mentioned"
assert_contains "$output" "escalat|user|stop" "Escalation path mentioned"
echo ""

# ------------------------------------------------------------------
# Test 7: product-state.md purpose
# ------------------------------------------------------------------
echo "Test 7: product-state.md tracking..."
output="$(run_claude \
  "What is the product-state.md file in ULI mode and when is it updated?" \
  "$timeout_seconds")"
assert_contains "$output" "product.state|product_state" "product-state file mentioned"
assert_contains "$output" "complet|ship|deliver|accept" "Updated after delivery/acceptance"
echo ""

# ------------------------------------------------------------------
# Test 8: Max iterations
# ------------------------------------------------------------------
echo "Test 8: Max iterations limit..."
output="$(run_claude \
  "What is the default max_iterations in ULI mode and what happens when it's reached?" \
  "$timeout_seconds")"
assert_contains "$output" "10\b|ten" "Default 10 iterations mentioned"
assert_contains "$output" "stop|done|complet|<uli-done>" "Termination condition described"
echo ""

echo "=== All ULI mode skill tests passed ==="
