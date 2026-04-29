#!/usr/bin/env bash
# E2E test: systematic-debugging skill
# Verifies Claude understands reproduce-first, hypothesis, bisect, root-cause tracing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: systematic-debugging skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Reproduce before anything else
# ------------------------------------------------------------------
echo "Test 1: Reproduce bug before fixing..."
output="$(run_claude \
  "According to systematic-debugging, what is the very first step when you encounter a bug?" \
  "$timeout_seconds")"
assert_contains "$output" "reproduc|repeat|confirm" "First step is reproduction"
echo ""

# ------------------------------------------------------------------
# Test 2: Hypothesis-driven approach
# ------------------------------------------------------------------
echo "Test 2: Hypothesis-driven debugging..."
output="$(run_claude \
  "What does systematic-debugging say about forming hypotheses? Should you guess and patch, or form a hypothesis first?" \
  "$timeout_seconds")"
assert_contains "$output" "hypothes|theory|predict|suspect" "Mentions hypothesis"
assert_contains "$output" "test.*hypothes|verify.*hypothes|confirm.*hypothes|falsif" \
  "Hypothesis must be tested"
echo ""

# ------------------------------------------------------------------
# Test 3: Root-cause, not symptom
# ------------------------------------------------------------------
echo "Test 3: Fix root cause, not symptom..."
output="$(run_claude \
  "In systematic-debugging, why is it wrong to just fix the symptom? What must you find first?" \
  "$timeout_seconds")"
assert_contains "$output" "root.*cause|underlying|actual.*cause|real.*cause" "Requires root cause"
assert_contains "$output" "symptom|workaround|band.aid" "Distinguishes symptom from cause"
echo ""

# ------------------------------------------------------------------
# Test 4: Binary search / bisect approach for regressions
# ------------------------------------------------------------------
echo "Test 4: Bisect / binary search for regressions..."
output="$(run_claude \
  "When debugging a regression, what search strategy does systematic-debugging recommend?" \
  "$timeout_seconds")"
assert_contains "$output" "bisect|binary.*search|git.*bisect|narrow.*down|half" \
  "Recommends bisect/binary search"
echo ""

# ------------------------------------------------------------------
# Test 5: Document findings
# ------------------------------------------------------------------
echo "Test 5: Document findings after debugging..."
output="$(run_claude \
  "After finding and fixing a bug, what does systematic-debugging say you should do?" \
  "$timeout_seconds")"
assert_contains "$output" "document|record|note|comment|explain|prevent|regression.*test" \
  "Requires documenting findings"
echo ""

echo "=== All systematic-debugging skill tests passed ==="
